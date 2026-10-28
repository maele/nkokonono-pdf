from __future__ import annotations

from pypdf import PdfReader, PdfWriter

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile


class MergeProcessor(BaseProcessor):
    tool_name = "merge-pdf"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if len(inputs) < 2:
            raise ProcessorError("INVALID_FILE", "At least two PDFs are required to merge.")

        by_id = {f.internal_id: f for f in inputs}
        readers: dict[str, PdfReader] = {}

        for f in inputs:
            try:
                reader = PdfReader(str(f.storage_path))
                if reader.is_encrypted:
                    raise ProcessorError(
                        "ENCRYPTED_PDF",
                        f"'{f.display_filename}' is encrypted; unlock it first.",
                    )
                readers[f.internal_id] = reader
            except ProcessorError:
                raise
            except Exception as exc:
                raise ProcessorError(
                    "INVALID_FILE", f"Could not read '{f.display_filename}': {exc}"
                )

        order = options.get("order")
        if order is None:
            return  # legacy path: all pages of all files

        if not isinstance(order, list) or not order:
            raise ProcessorError(
                "INVALID_PAGE_RANGE", "Provide at least one page in the order."
            )
        for entry in order:
            if not isinstance(entry, dict):
                raise ProcessorError("INVALID_PAGE_RANGE", "Invalid order entry.")
            file_id = entry.get("file_id")
            page = entry.get("page")
            rotation = entry.get("rotation", 0)
            if file_id not in by_id:
                raise ProcessorError("INVALID_FILE", "Unknown file in order.")
            total = len(readers[file_id].pages)
            if not isinstance(page, int) or page < 1 or page > total:
                raise ProcessorError(
                    "INVALID_PAGE_RANGE", f"Page {page} out of range 1-{total}."
                )
            if rotation not in (0, 90, 180, 270):
                raise ProcessorError(
                    "INVALID_FILE", "Rotation must be 0, 90, 180, or 270."
                )

    def process(self, inputs, options, output_dir):
        by_id = {f.internal_id: f for f in inputs}
        order = options.get("order")

        writer = PdfWriter()

        if order:
            for entry in order:
                file_id = entry["file_id"]
                page_num = entry["page"]
                rotation = entry.get("rotation", 0)
                reader = PdfReader(str(by_id[file_id].storage_path))
                writer.add_page(reader.pages[page_num - 1])
                if rotation:
                    writer.pages[-1].rotate(rotation)
        else:
            for f in inputs:
                reader = PdfReader(str(f.storage_path))
                for page in reader.pages:
                    writer.add_page(page)

        out = output_dir / "merged.pdf"
        try:
            with open(out, "wb") as fh:
                writer.write(fh)
        except Exception as exc:
            raise ProcessorError("PROCESSING_FAILED", f"Failed to write merged PDF: {exc}")

        return [ProcessorOutput(path=out, display_name="merged.pdf", mime_type="application/pdf")]
