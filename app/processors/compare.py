from __future__ import annotations

import difflib
from pathlib import Path

from pypdf import PdfReader

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput


class CompareProcessor(BaseProcessor):
    tool_name = "compare-pdf"

    def validate(self, inputs, options):
        if len(inputs) != 2:
            raise ProcessorError("INVALID_FILE", "Compare requires exactly two PDFs.")
        for f in inputs:
            try:
                r = PdfReader(str(f.storage_path))
                if r.is_encrypted:
                    raise ProcessorError("ENCRYPTED_PDF", "Compare does not support encrypted PDFs.")
            except ProcessorError:
                raise
            except Exception as exc:
                raise ProcessorError("INVALID_FILE", f"Could not read '{f.display_filename}': {exc}")

    def process(self, inputs, options, output_dir):
        a, b = inputs
        reader_a = PdfReader(str(a.storage_path))
        reader_b = PdfReader(str(b.storage_path))
        pages_a = [p.extract_text() or "" for p in reader_a.pages]
        pages_b = [p.extract_text() or "" for p in reader_b.pages]

        lines = [
            f"Comparison report",
            f"A: {a.display_filename} — {len(pages_a)} page(s)",
            f"B: {b.display_filename} — {len(pages_b)} page(s)",
            "",
        ]

        if len(pages_a) != len(pages_b):
            lines.append(f"Page counts differ: {len(pages_a)} vs {len(pages_b)}")
            lines.append("")

        total_pages = min(len(pages_a), len(pages_b))
        for idx in range(total_pages):
            ta, tb = pages_a[idx], pages_b[idx]
            if ta == tb:
                lines.append(f"Page {idx + 1}: identical")
                continue
            lines.append(f"Page {idx + 1}: differences")
            diff = difflib.unified_diff(
                ta.splitlines(),
                tb.splitlines(),
                fromfile=f"page-{idx + 1}-A",
                tofile=f"page-{idx + 1}-B",
                lineterm="",
            )
            lines.extend(diff)
            lines.append("")

        if len(pages_a) > total_pages:
            lines.append(f"Only in A: pages {total_pages + 1}..{len(pages_a)}")
        if len(pages_b) > total_pages:
            lines.append(f"Only in B: pages {total_pages + 1}..{len(pages_b)}")

        out = output_dir / "comparison.txt"
        out.write_text("\n".join(lines), encoding="utf-8")
        return [ProcessorOutput(path=out, display_name="comparison.txt", mime_type="text/plain")]