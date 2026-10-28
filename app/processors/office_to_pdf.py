from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput


class OfficeToPdfProcessor(BaseProcessor):
    soffice_binary = "libreoffice"

    def validate(self, inputs, options):
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Convert exactly one Office document at a time.")
        if shutil.which(self.soffice_binary) is None:
            raise ProcessorError(
                "CONVERSION_FAILED",
                "LibreOffice is not installed on the server.",
            )

    def process(self, inputs, options, output_dir):
        input_path = inputs[0].storage_path
        profile_dir = Path(tempfile.mkdtemp(prefix="lo-profile-"))
        try:
            cmd = [
                self.soffice_binary,
                "--headless",
                "--norestore",
                "--nolockcheck",
                "--nodefault",
                "--nofirststartwizard",
                f"-env:UserInstallation=file://{profile_dir}",
                "--convert-to", "pdf",
                "--outdir", str(output_dir),
                str(input_path),
            ]
            try:
                subprocess.run(cmd, timeout=120, check=True, capture_output=True)
            except subprocess.TimeoutExpired:
                raise ProcessorError("PROCESSING_TIMEOUT", "Office conversion exceeded the time limit.")
            except subprocess.CalledProcessError as exc:
                raise ProcessorError(
                    "CONVERSION_FAILED",
                    f"LibreOffice failed: {exc.stderr.decode(errors='ignore')[:200]}",
                )

            expected = output_dir / f"{input_path.stem}.pdf"
            if not expected.exists():
                candidates = list(output_dir.glob("*.pdf"))
                if not candidates:
                    raise ProcessorError("CONVERSION_FAILED", "LibreOffice did not produce a PDF.")
                expected = candidates[0]

            final = output_dir / "converted.pdf"
            if expected != final:
                expected.rename(final)

            try:
                PdfReader(str(final))
            except Exception as exc:
                raise ProcessorError("OUTPUT_VALIDATION_FAILED", f"Invalid PDF produced: {exc}")

            return [ProcessorOutput(path=final, display_name="converted.pdf", mime_type="application/pdf")]
        finally:
            shutil.rmtree(profile_dir, ignore_errors=True)


class WordToPdfProcessor(OfficeToPdfProcessor):
    tool_name = "word-to-pdf"


class ExcelToPdfProcessor(OfficeToPdfProcessor):
    tool_name = "excel-to-pdf"


class PptToPdfProcessor(OfficeToPdfProcessor):
    tool_name = "ppt-to-pdf"