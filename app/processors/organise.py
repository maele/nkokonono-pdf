from __future__ import annotations

import json

from pypdf import PdfReader, PdfWriter

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile


def _as_int_list(value) -> list[int]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [int(x) for x in value]
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                return [int(x) for x in json.loads(s)]
            except Exception:
                pass
        return [int(x.strip()) for x in s.split(",") if x.strip()]
    raise ProcessorError("INVALID_FILE", "Expected a list of integers.")


def _as_rotation_map(value) -> dict[int, int]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return {int(k): int(v) for k, v in value.items()}
    if isinstance(value, str):
        result: dict[int, int] = {}
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" not in part:
                raise ProcessorError("INVALID_FILE", f"Invalid rotation entry: {part!r}.")
            k, _, v = part.partition(":")
            result[int(k)] = int(v)
        return result
    raise ProcessorError("INVALID_FILE", "Invalid rotations.")


class OrganiseProcessor(BaseProcessor):
    tool_name = "organise-pdf"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Organise accepts exactly one PDF.")
        try:
            order = _as_int_list(options.get("order"))
            rotations = _as_rotation_map(options.get("rotations"))
            rotation_list = _as_int_list(options.get("rotation_list"))
        except (TypeError, ValueError) as exc:
            raise ProcessorError("INVALID_PAGE_RANGE", f"Invalid page specification: {exc}")

        if not order:
            raise ProcessorError("INVALID_PAGE_RANGE", "Provide at least one page.")

        if rotation_list and len(rotation_list) != len(order):
            raise ProcessorError(
                "INVALID_FILE",
                "rotation_list must be the same length as order.",
            )

        for angle in rotation_list:
            if angle not in (0, 90, 180, 270):
                raise ProcessorError("INVALID_FILE", "Rotation must be 0, 90, 180, or 270.")

        try:
            reader = PdfReader(str(inputs[0].storage_path))
            if reader.is_encrypted:
                raise ProcessorError("ENCRYPTED_PDF", "Organise does not support encrypted PDFs.")
            total = len(reader.pages)
            for p in order:
                if not (1 <= p <= total):
                    raise ProcessorError("INVALID_PAGE_RANGE", f"Page {p} out of range 1-{total}.")
            for p, angle in rotations.items():
                if not (1 <= p <= total):
                    raise ProcessorError("INVALID_PAGE_RANGE", f"Page {p} out of range 1-{total}.")
                if angle not in (0, 90, 180, 270):
                    raise ProcessorError("INVALID_FILE", "Rotation must be 0, 90, 180, or 270.")
        except ProcessorError:
            raise
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        reader = PdfReader(str(inputs[0].storage_path))
        order = _as_int_list(options["order"])
        rotations = _as_rotation_map(options.get("rotations"))
        rotation_list = _as_int_list(options.get("rotation_list"))

        writer = PdfWriter()
        for i, source in enumerate(order):
            # add_page() snapshots the page state into the writer. Rotate the
            # writer's copy, not the reader's page — otherwise repeated access
            # to the same source page (duplicates) would accumulate rotation.
            writer.add_page(reader.pages[source - 1])
            if rotation_list:
                angle = rotation_list[i] if i < len(rotation_list) else 0
            else:
                angle = rotations.get(source, 0)
            if angle:
                writer.pages[-1].rotate(angle)

        out = output_dir / "organised.pdf"
        with open(out, "wb") as fh:
            writer.write(fh)
        return [ProcessorOutput(path=out, display_name="organised.pdf", mime_type="application/pdf")]
