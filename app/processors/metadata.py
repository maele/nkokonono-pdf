from __future__ import annotations

from pypdf import PdfReader, PdfWriter

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile

FIELD_MAP = {
    "title": "/Title",
    "author": "/Author",
    "subject": "/Subject",
    "keywords": "/Keywords",
    "creator": "/Creator",
}


class MetadataProcessor(BaseProcessor):
    tool_name = "pdf-metadata"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Metadata accepts exactly one PDF.")
        try:
            PdfReader(str(inputs[0].storage_path))
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        reader = PdfReader(str(inputs[0].storage_path))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        if options.get("clear"):
            final: dict[str, str] = {}
        else:
            final = {}
            if reader.metadata:
                for k, v in reader.metadata.items():
                    if k and v is not None and str(v) != "":
                        final[k] = str(v)

        for opt_key, pdf_key in FIELD_MAP.items():
            if opt_key in options:
                value = str(options[opt_key]).strip()
                if value:
                    final[pdf_key] = value
                else:
                    final.pop(pdf_key, None)

        if final:
            writer.add_metadata(final)

        out = output_dir / "metadata.pdf"
        with open(out, "wb") as fh:
            writer.write(fh)
        return [ProcessorOutput(path=out, display_name="metadata.pdf", mime_type="application/pdf")]