from __future__ import annotations

from pypdf import PdfReader, PdfWriter

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile
from app.utils.validators import parse_page_range


class ExtractProcessor(BaseProcessor):
    tool_name = "extract-pages"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Extract accepts exactly one PDF.")
        pages = str(options.get("pages", "")).strip()
        if not pages:
            raise ProcessorError("INVALID_PAGE_RANGE", "Provide pages like 1-3,5.")
        try:
            reader = PdfReader(str(inputs[0].storage_path))
            if reader.is_encrypted:
                raise ProcessorError("ENCRYPTED_PDF", "Extract does not support encrypted PDFs.")
            parse_page_range(pages, len(reader.pages))
        except ProcessorError:
            raise
        except ValueError as exc:
            raise ProcessorError("INVALID_PAGE_RANGE", str(exc))
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        reader = PdfReader(str(inputs[0].storage_path))
        pages = parse_page_range(str(options["pages"]), len(reader.pages))
        writer = PdfWriter()
        for p in pages:
            writer.add_page(reader.pages[p - 1])
        out = output_dir / "extracted.pdf"
        with open(out, "wb") as fh:
            writer.write(fh)
        return [ProcessorOutput(path=out, display_name="extracted.pdf", mime_type="application/pdf")]