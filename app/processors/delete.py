from __future__ import annotations

from pypdf import PdfReader, PdfWriter

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile
from app.utils.validators import parse_page_range


class DeleteProcessor(BaseProcessor):
    tool_name = "delete-pages"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Delete accepts exactly one PDF.")
        pages = str(options.get("pages", "")).strip()
        if not pages:
            raise ProcessorError("INVALID_PAGE_RANGE", "Provide pages to delete.")
        try:
            reader = PdfReader(str(inputs[0].storage_path))
            if reader.is_encrypted:
                raise ProcessorError("ENCRYPTED_PDF", "Delete does not support encrypted PDFs.")
            total = len(reader.pages)
            to_delete = parse_page_range(pages, total)
            if len(to_delete) >= total:
                raise ProcessorError("INVALID_PAGE_RANGE", "Cannot delete every page.")
        except ProcessorError:
            raise
        except ValueError as exc:
            raise ProcessorError("INVALID_PAGE_RANGE", str(exc))
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        reader = PdfReader(str(inputs[0].storage_path))
        total = len(reader.pages)
        to_delete = set(parse_page_range(str(options["pages"]), total))
        writer = PdfWriter()
        for i, page in enumerate(reader.pages, start=1):
            if i not in to_delete:
                writer.add_page(page)
        out = output_dir / "updated.pdf"
        with open(out, "wb") as fh:
            writer.write(fh)
        return [ProcessorOutput(path=out, display_name="updated.pdf", mime_type="application/pdf")]