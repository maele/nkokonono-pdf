from __future__ import annotations

from pypdf import PdfReader, PdfWriter

from app.processors.base import BaseProcessor, ProcessorError, ProcessorOutput
from app.services.file_service import StoredFile


class ProtectProcessor(BaseProcessor):
    tool_name = "protect-pdf"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Protect accepts exactly one PDF.")
        password = str(options.get("password", ""))
        if len(password) < 4:
            raise ProcessorError("INVALID_FILE", "Password must be at least 4 characters.")
        try:
            reader = PdfReader(str(inputs[0].storage_path))
            if reader.is_encrypted:
                raise ProcessorError("ENCRYPTED_PDF", "File is already encrypted.")
        except ProcessorError:
            raise
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        reader = PdfReader(str(inputs[0].storage_path))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(user_password=str(options["password"]), algorithm="AES-256")
        out = output_dir / "protected.pdf"
        with open(out, "wb") as fh:
            writer.write(fh)
        return [ProcessorOutput(path=out, display_name="protected.pdf", mime_type="application/pdf")]


class UnlockProcessor(BaseProcessor):
    tool_name = "unlock-pdf"

    def validate(self, inputs: list[StoredFile], options: dict) -> None:
        if len(inputs) != 1:
            raise ProcessorError("INVALID_FILE", "Unlock accepts exactly one PDF.")
        try:
            reader = PdfReader(str(inputs[0].storage_path))
            if not reader.is_encrypted:
                raise ProcessorError(
                    "INVALID_FILE", "This PDF is not encrypted; there is nothing to unlock."
                )
        except ProcessorError:
            raise
        except Exception as exc:
            raise ProcessorError("INVALID_FILE", f"Could not read PDF: {exc}")

    def process(self, inputs, options, output_dir):
        reader = PdfReader(str(inputs[0].storage_path))
        if reader.is_encrypted:
            if reader.decrypt(str(options.get("password", ""))) == 0:
                raise ProcessorError("ENCRYPTED_PDF", "The supplied password is incorrect.")
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        out = output_dir / "unlocked.pdf"
        with open(out, "wb") as fh:
            writer.write(fh)
        return [ProcessorOutput(path=out, display_name="unlocked.pdf", mime_type="application/pdf")]