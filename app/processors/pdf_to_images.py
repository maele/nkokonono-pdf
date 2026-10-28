from __future__ import annotations

import zipfile

import fitz  # PyMuPDF

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile
from app.utils.validators import parse_page_range


class PdfToImagesProcessor(BaseProcessor):
    tool_name = "pdf-to-images"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "PDF to images accepts exactly one PDF.")
        fmt = options.get("format", "png")
        if fmt not in {"png", "jpeg"}:
            raise ProcessorError("INVALID_FILE", "Format must be png or jpeg.")
        try:
            dpi = int(options.get("dpi", 150))
        except (TypeError, ValueError):
            raise ProcessorError("INVALID_FILE", "DPI must be an integer.")
        if not (72 <= dpi <= 600):
            raise ProcessorError("INVALID_FILE", "DPI must be between 72 and 600.")
        pages = str(options.get("pages", "")).strip()
        try:
            doc = fitz.open(str(inputs[0].storage_path))
            if doc.is_encrypted:
                raise ProcessorError("ENCRYPTED_PDF", "PDF to images does not support encrypted PDFs.")
            if pages:
                parse_page_range(pages, doc.page_count)
            doc.close()
        except ProcessorError:
            raise
        except ValueError as exc:
            raise ProcessorError("INVALID_PAGE_RANGE", str(exc))
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        doc = fitz.open(str(inputs[0].storage_path))
        fmt = options.get("format", "png")
        dpi = int(options.get("dpi", 150))
        pages = str(options.get("pages", "")).strip()
        indices = (
            [p - 1 for p in parse_page_range(pages, doc.page_count)]
            if pages else list(range(doc.page_count))
        )

        ext = "png" if fmt == "png" else "jpg"
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        produced = []
        try:
            for idx in indices:
                page = doc.load_page(idx)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                p = output_dir / f"page-{idx + 1:03d}.{ext}"
                pix.save(str(p))
                produced.append(p)
        finally:
            doc.close()

        if len(produced) == 1:
            mime = "image/png" if fmt == "png" else "image/jpeg"
            return [ProcessorOutput(path=produced[0], display_name=produced[0].name, mime_type=mime)]

        zip_path = output_dir / "pages.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in produced:
                zf.write(f, f.name)
                f.unlink(missing_ok=True)
        return [ProcessorOutput(path=zip_path, display_name="pages.zip", mime_type="application/zip")]