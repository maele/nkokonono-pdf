from __future__ import annotations

import io
import shutil
from pathlib import Path

from PIL import Image

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile


PROFILES = {
    "smaller":     {"max_dim": 1200, "quality": 55},
    "recommended": {"max_dim": 1600, "quality": 70},
    "higher":      {"max_dim": 2200, "quality": 85},
}


class CompressProcessor(BaseProcessor):
    tool_name = "compress-pdf"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Compress accepts exactly one PDF.")
        profile = options.get("profile", "recommended")
        if profile not in PROFILES:
            raise ProcessorError(
                "INVALID_FILE",
                f"Invalid compression profile '{profile}'. "
                f"Expected one of: {', '.join(PROFILES)}.",
            )
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(inputs[0].storage_path))
            if reader.is_encrypted:
                raise ProcessorError("ENCRYPTED_PDF", "Compress does not support encrypted PDFs.")
        except ProcessorError:
            raise
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ProcessorError("CONVERSION_FAILED", "PyMuPDF is not available.")

        profile = options.get("profile", "recommended")
        cfg = PROFILES[profile]
        original_path = inputs[0].storage_path
        original_size = original_path.stat().st_size

        # ---- Stage 1: image recompression + stream deflation --------------
        stage1 = output_dir / "stage1.pdf"
        try:
            doc = fitz.open(str(original_path))
            self._process_images(doc, cfg)
            doc.save(
                str(stage1),
                deflate=True,
                garbage=4,
                clean=True,
                deflate_images=True,
                deflate_fonts=True,
            )
            doc.close()
        except Exception as exc:
            raise ProcessorError("PROCESSING_FAILED", f"PDF compression failed: {exc}")

        # ---- Stage 2: structural optimisation via pikepdf (optional) ------
        final = output_dir / "compressed.pdf"
        try:
            import pikepdf
            with pikepdf.open(str(stage1)) as pdf:
                pdf.save(
                    str(final),
                    compress_streams=True,
                    recompress_flate=True,
                    object_stream_mode=pikepdf.ObjectStreamMode.generate,
                )
            stage1.unlink(missing_ok=True)
        except ImportError:
            shutil.move(str(stage1), str(final))
        except Exception:
            if stage1.exists():
                shutil.move(str(stage1), str(final))

        # ---- Stage 3: keep result only if it is actually smaller ----------
        if final.stat().st_size >= original_size:
            shutil.copy(original_path, final)
            note = (
                f"Compression did not reduce the file size — this PDF is already "
                f"well optimised ({self._human(original_size)}). "
                f"The original file is returned unchanged."
            )
        else:
            new_size = final.stat().st_size
            ratio = 100 * (1 - new_size / original_size)
            note = (
                f"Reduced from {self._human(original_size)} to "
                f"{self._human(new_size)} — {ratio:.0f}% smaller."
            )

        return [ProcessorOutput(
            path=final,
            display_name="compressed.pdf",
            mime_type="application/pdf",
            notes=note,
        )]

    # ---------------------------------------------------------------- internals

    def _process_images(self, doc, cfg):
        seen: set[int] = set()
        for page_idx in range(doc.page_count):
            page = doc[page_idx]
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                smask = img_info[1]
                if xref in seen:
                    continue
                if smask:
                    continue
                seen.add(xref)
                try:
                    self._compress_image(doc, page, xref, cfg)
                except Exception:
                    continue

    def _compress_image(self, doc, page, xref, cfg):
        img_data = doc.extract_image(xref)
        if not img_data:
            return
        original_bytes = img_data["image"]

        if img_data["width"] < 64 or img_data["height"] < 64:
            return
        if len(original_bytes) < 5000:
            return

        try:
            img = Image.open(io.BytesIO(original_bytes))
        except Exception:
            return

        w, h = img.size
        if max(w, h) > cfg["max_dim"]:
            ratio = cfg["max_dim"] / max(w, h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        elif img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=cfg["quality"], optimize=True)
        new_bytes = buf.getvalue()

        if len(new_bytes) < len(original_bytes) * 0.9:
            try:
                page.replace_image(xref, stream=new_bytes)
            except Exception:
                pass

    @staticmethod
    def _human(n: int) -> str:
        if n < 1024:
            return f"{n} B"
        if n < 1024 * 1024:
            return f"{n / 1024:.1f} KB"
        return f"{n / (1024 * 1024):.2f} MB"
