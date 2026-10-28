from pathlib import Path

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput


class OcrProcessor(BaseProcessor):
    tool_name = "ocr-pdf"

    def validate(self, inputs, options):
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "OCR accepts exactly one PDF.")
        try:
            import ocrmypdf  # noqa: F401
        except ImportError:
            raise ProcessorError("CONVERSION_FAILED", "OCRmyPDF is not installed.")
        lang = str(options.get("language", "eng")).strip()
        if not lang:
            raise ProcessorError("INVALID_FILE", "Language is required.")

    def process(self, inputs, options, output_dir):
        import ocrmypdf

        language = str(options.get("language", "eng")).strip()
        force = bool(options.get("force", True))
        out = output_dir / "ocr.pdf"
        try:
            ocrmypdf.ocr(
                str(inputs[0].storage_path),
                str(out),
                language=language,
                force_ocr=force,
                deskew=True,
                clean=True,
                progress_bar=False,
                use_threads=False,
            )
        except ocrmypdf.exceptions.EncryptedPdfError:
            raise ProcessorError("ENCRYPTED_PDF", "OCR does not support encrypted PDFs.")
        except ocrmypdf.exceptions.PriorOcrFoundError:
            raise ProcessorError(
                "INVALID_FILE",
                "This PDF already contains a text layer. Enable 'force' to OCR anyway.",
            )
        except ocrmypdf.exceptions.BadArgsError as exc:
            raise ProcessorError("CONVERSION_FAILED", f"OCR configuration error: {exc}")
        except Exception as exc:
            raise ProcessorError("CONVERSION_FAILED", f"OCR failed: {exc}")
        if not out.exists():
            raise ProcessorError("OUTPUT_VALIDATION_FAILED", "No PDF was produced.")
        return [ProcessorOutput(path=out, display_name="ocr.pdf", mime_type="application/pdf")]