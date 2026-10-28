from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile


class WatermarkProcessor(BaseProcessor):
    tool_name = "watermark-pdf"

    def validate(self, inputs, options):
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Watermark accepts exactly one PDF.")
        text = str(options.get("text", "")).strip()
        if not text:
            raise ProcessorError("INVALID_FILE", "Watermark text is required.")
        try:
            reader = PdfReader(str(inputs[0].storage_path))
            if reader.is_encrypted:
                raise ProcessorError("ENCRYPTED_PDF", "Watermark does not support encrypted PDFs.")
            if len(reader.pages) == 0:
                raise ProcessorError("INVALID_FILE", "The PDF has no pages.")
        except ProcessorError:
            raise
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        text = str(options["text"]).strip()
        opacity = float(options.get("opacity", 0.3))
        font_size = int(options.get("font_size", 48))

        reader = PdfReader(str(inputs[0].storage_path))
        writer = PdfWriter()
        for page in reader.pages:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            overlay = io.BytesIO()
            c = canvas.Canvas(overlay, pagesize=(width, height))
            c.saveState()
            c.translate(width / 2, height / 2)
            c.rotate(45)
            c.setFont("Helvetica-Bold", font_size)
            c.setFillColor(HexColor("#888888"), alpha=opacity)
            c.drawCentredString(0, 0, text)
            c.restoreState()
            c.save()
            overlay.seek(0)
            page.merge_page(PdfReader(overlay).pages[0])
            writer.add_page(page)

        out = output_dir / "watermarked.pdf"
        with open(out, "wb") as fh:
            writer.write(fh)
        return [ProcessorOutput(path=out, display_name="watermarked.pdf", mime_type="application/pdf")]