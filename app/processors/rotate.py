from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile
from app.utils.validators import parse_page_range


class RotateProcessor(BaseProcessor):
    tool_name = "rotate-pdf"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Rotate accepts exactly one PDF.")
        try:
            angle = int(options.get("angle", 90))
        except (TypeError, ValueError):
            raise ProcessorError("INVALID_FILE", "Angle must be 90, 180, or 270.")
        if angle not in (90, 180, 270):
            raise ProcessorError("INVALID_FILE", "Angle must be 90, 180, or 270.")
        try:
            reader = PdfReader(str(inputs[0].storage_path))
            if reader.is_encrypted:
                raise ProcessorError("ENCRYPTED_PDF", "Rotate does not support encrypted PDFs.")
            pages = str(options.get("pages", "")).strip()
            if pages:
                parse_page_range(pages, len(reader.pages))
        except ProcessorError:
            raise
        except ValueError as exc:
            raise ProcessorError("INVALID_PAGE_RANGE", str(exc))
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        reader = PdfReader(str(inputs[0].storage_path))
        total = len(reader.pages)
        angle = int(options.get("angle", 90))
        pages = str(options.get("pages", "")).strip()
        targets = set(parse_page_range(pages, total)) if pages else set(range(1, total + 1))
        writer = PdfWriter()
        for i, page in enumerate(reader.pages, start=1):
            if i in targets:
                page.rotate(angle)
            writer.add_page(page)
        out = output_dir / "rotated.pdf"
        with open(out, "wb") as fh:
            writer.write(fh)
        return [ProcessorOutput(path=out, display_name="rotated.pdf", mime_type="application/pdf")]