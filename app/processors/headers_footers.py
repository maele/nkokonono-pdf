from __future__ import annotations

import io

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput


class HeadersFootersProcessor(BaseProcessor):
    tool_name = "headers-footers"

    def validate(self, inputs, options):
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Headers & footers accepts exactly one PDF.")
        if not (str(options.get("header", "")).strip() or str(options.get("footer", "")).strip()):
            raise ProcessorError("INVALID_FILE", "Provide a header or footer.")
        try:
            reader = PdfReader(str(inputs[0].storage_path))
            if reader.is_encrypted:
                raise ProcessorError("ENCRYPTED_PDF", "Headers & footers does not support encrypted PDFs.")
        except ProcessorError:
            raise
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        header = str(options.get("header", "")).strip()
        footer = str(options.get("footer", "")).strip()
        reader = PdfReader(str(inputs[0].storage_path))
        writer = PdfWriter()

        for page in reader.pages:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            overlay = io.BytesIO()
            c = canvas.Canvas(overlay, pagesize=(width, height))
            c.setFont("Helvetica", 9)
            c.setFillColor(HexColor("#555555"))
            if header:
                c.drawCentredString(width / 2, height - 24, header)
            if footer:
                c.drawCentredString(width / 2, 20, footer)
            c.save()
            overlay.seek(0)
            page.merge_page(PdfReader(overlay).pages[0])
            writer.add_page(page)

        out = output_dir / "with-headers-footers.pdf"
        with open(out, "wb") as fh:
            writer.write(fh)
        return [ProcessorOutput(path=out, display_name="with-headers-footers.pdf", mime_type="application/pdf")]