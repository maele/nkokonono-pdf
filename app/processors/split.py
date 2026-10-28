from __future__ import annotations

import zipfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile
from app.utils.validators import parse_page_range


class SplitProcessor(BaseProcessor):
    tool_name = "split-pdf"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Split accepts exactly one PDF.")
        mode = options.get("mode", "every")
        if mode not in {"every", "ranges"}:
            raise ProcessorError("INVALID_FILE", "Mode must be 'every' or 'ranges'.")
        try:
            reader = PdfReader(str(inputs[0].storage_path))
            if reader.is_encrypted:
                raise ProcessorError("ENCRYPTED_PDF", "Split does not support encrypted PDFs.")
            total = len(reader.pages)
            if total == 0:
                raise ProcessorError("INVALID_FILE", "The PDF has no pages.")
            if mode == "ranges":
                raw = options.get("ranges", "")
                if not raw.strip():
                    raise ProcessorError("INVALID_PAGE_RANGE", "Provide ranges like 1-3,5.")
                for part in raw.split(","):
                    if part.strip():
                        parse_page_range(part.strip(), total)
        except ProcessorError:
            raise
        except ValueError as exc:
            raise ProcessorError("INVALID_PAGE_RANGE", str(exc))
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        mode = options.get("mode", "every")
        reader = PdfReader(str(inputs[0].storage_path))
        total = len(reader.pages)
        produced: list[Path] = []

        if mode == "every":
            for i in range(total):
                writer = PdfWriter()
                writer.add_page(reader.pages[i])
                p = output_dir / f"page-{i + 1:03d}.pdf"
                with open(p, "wb") as fh:
                    writer.write(fh)
                produced.append(p)
        else:
            for idx, part in enumerate(options["ranges"].split(","), start=1):
                part = part.strip()
                if not part:
                    continue
                pages = parse_page_range(part, total)
                writer = PdfWriter()
                for pnum in pages:
                    writer.add_page(reader.pages[pnum - 1])
                safe = part.replace("-", "_").replace(",", "_").replace(" ", "")
                p = output_dir / f"range-{idx:02d}-{safe}.pdf"
                with open(p, "wb") as fh:
                    writer.write(fh)
                produced.append(p)

        if len(produced) == 1:
            return [ProcessorOutput(path=produced[0], display_name=produced[0].name, mime_type="application/pdf")]

        zip_path = output_dir / "split.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in produced:
                zf.write(f, f.name)
                f.unlink(missing_ok=True)
        return [ProcessorOutput(path=zip_path, display_name="split.zip", mime_type="application/zip")]