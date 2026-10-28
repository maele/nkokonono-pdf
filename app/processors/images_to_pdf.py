from __future__ import annotations

from pathlib import Path

from PIL import Image

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile

# Page sizes in pixels at 300 dpi.
PAGE_SIZES = {
    "a4": (2480, 3508),
    "letter": (2550, 3300),
}
MARGIN_PX = 236  # ~20 mm at 300 dpi
OUTPUT_DPI = 300


class ImagesToPdfProcessor(BaseProcessor):
    tool_name = "images-to-pdf"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if not inputs:
            raise ProcessorError("INVALID_FILE", "Upload at least one image.")
        page_size = options.get("page_size", "auto")
        if page_size not in {"auto", "a4", "letter"}:
            raise ProcessorError("INVALID_FILE", "Page size must be auto, a4, or letter.")
        for f in inputs:
            try:
                with Image.open(f.storage_path) as img:
                    img.verify()
            except Exception as exc:
                raise ProcessorError("INVALID_FILE", f"'{f.display_filename}' is not a valid image: {exc}")

    def process(self, inputs, options, output_dir):
        page_size = options.get("page_size", "auto")
        pages: list[Image.Image] = []
        for f in inputs:
            img = Image.open(f.storage_path)
            img.load()
            rgb = img.convert("RGB") if img.mode != "RGB" else img
            if page_size == "auto":
                pages.append(rgb.copy())
            else:
                cw, ch = PAGE_SIZES[page_size]
                canvas = Image.new("RGB", (cw, ch), "white")
                fitted = rgb.copy()
                fitted.thumbnail((cw - 2 * MARGIN_PX, ch - 2 * MARGIN_PX), Image.LANCZOS)
                x = (cw - fitted.width) // 2
                y = (ch - fitted.height) // 2
                canvas.paste(fitted, (x, y))
                pages.append(canvas)

        if not pages:
            raise ProcessorError("OUTPUT_VALIDATION_FAILED", "No images to convert.")

        out = output_dir / "images.pdf"
        save_kwargs = {"save_all": True, "append_images": pages[1:], "resolution": OUTPUT_DPI}
        try:
            pages[0].save(str(out), "PDF", **save_kwargs)
        except Exception as exc:
            raise ProcessorError("PROCESSING_FAILED", f"Failed to write PDF: {exc}")
        return [ProcessorOutput(path=out, display_name="images.pdf", mime_type="application/pdf")]