from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile

POSITIONS = {"bottom-center", "bottom-right", "bottom-left", "top-center", "top-right", "top-left"}


class PageNumbersProcessor(BaseProcessor):
    tool_name = "page-numbers"

    def validate(self, inputs, options):
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Page numbers accepts exactly one PDF.")
        position = options.get("position", "bottom-center")
        if position not in POSITIONS:
            raise ProcessorError("INVALID_FILE", "Invalid position.")
        try:
            reader = PdfReader(str(inputs[0].storage_path))
            if reader.is_encrypted:
                raise ProcessorError("ENCRYPTED_PDF", "Page numbers does not support encrypted PDFs.")
        except ProcessorError:
            raise
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        position = options.get("position", "bottom-center")
        start = int(options.get("start", 1))
        prefix = str(options.get("prefix", ""))
        reader = PdfReader(str(inputs[0].storage_path))
        writer = PdfWriter()
        total = len(reader.pages)

        for i, page in enumerate(reader.pages):
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            label = f"{prefix}{start + i}"

            overlay = io.BytesIO()
            c = canvas.Canvas(overlay, pagesize=(width, height))
            c.setFont("Helvetica", 10)
            c.setFillColor(HexColor("#333333"))
            margin = 20
            if position.endswith("center"):
                x, align = width / 2, "center"
            elif position.endswith("right"):
                x, align = width - margin, "right"
            else:
                x, align = margin, "left"
            y = height - 20 if position.startswith("top") else 20

            if align == "center":
                c.drawCentredString(x, y, label)
            elif align == "right":
                c.drawRightString(x, y, label)
            else:
                c.drawString(x, y, label)
            c.save()
            overlay.seek(0)
            page.merge_page(PdfReader(overlay).pages[0])
            writer.add_page(page)

        out = output_dir / "numbered.pdf"
        with open(out, "wb") as fh:
            writer.write(fh)
        return [ProcessorOutput(path=out, display_name="numbered.pdf", mime_type="application/pdf")]