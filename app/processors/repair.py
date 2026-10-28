from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput


class RepairProcessor(BaseProcessor):
    tool_name = "repair-pdf"

    def validate(self, inputs, options):
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Repair accepts exactly one PDF.")

    def process(self, inputs, options, output_dir):
        try:
            reader = PdfReader(str(inputs[0].storage_path), strict=False)
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not open the PDF for repair: {exc}")

        writer = PdfWriter()
        recovered = 0
        for page in reader.pages:
            try:
                writer.add_page(page)
                recovered += 1
            except Exception:
                continue

        if recovered == 0:
            raise ProcessorError("CONVERSION_FAILED", "No pages could be recovered from this PDF.")

        out = output_dir / "repaired.pdf"
        try:
            with open(out, "wb") as fh:
                writer.write(fh)
        except Exception as exc:
            raise ProcessorError("CONVERSION_FAILED", f"Could not write repaired PDF: {exc}")

        return [ProcessorOutput(path=out, display_name="repaired.pdf", mime_type="application/pdf")]