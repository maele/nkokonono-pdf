from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage

from app.utils.filenames import (
    generate_internal_id,
    get_safe_extension,
    sanitize_display_filename,
)
from app.utils.validators import (
    validate_html_file,
    validate_image_file,
    validate_ole_file,
    validate_ooxml_file,
    validate_pdf_file,
)

log = logging.getLogger(__name__)

# Extension -> MIME type for the accepted non-PDF, non-image families.
OOXML_MIME = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}
OLE_MIME = {
    ".doc": "application/msword",
    ".xls": "application/vnd.ms-excel",
    ".ppt": "application/vnd.ms-powerpoint",
}
HTML_EXTENSIONS = {".html", ".htm"}


@dataclass
class StoredFile:
    internal_id: str
    original_filename: str
    display_filename: str
    extension: str
    mime_type: str
    size_bytes: int
    storage_path: Path
    tool: str
    uploaded_at: datetime
    expires_at: datetime


class FileValidationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class FileService:
    def __init__(self, storage_root: str | Path | None = None) -> None:
        self._storage_root = Path(storage_root or current_app.config["STORAGE_ROOT"])

    @property
    def storage_root(self) -> Path:
        self._storage_root.mkdir(parents=True, exist_ok=True)
        return self._storage_root

    def temporary_dir(self) -> Path:
        path = self.storage_root / "temporary"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def output_dir(self) -> Path:
        path = self.storage_root / "output"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def store_upload(self, file: FileStorage, tool: str) -> StoredFile:
        if not file or not file.filename:
            raise FileValidationError("INVALID_FILE", "No file was provided.")

        display = sanitize_display_filename(file.filename)
        ext = get_safe_extension(display)
        if not ext:
            raise FileValidationError("UNSUPPORTED_FORMAT", "The file has no usable extension.")

        internal_id = generate_internal_id()
        job_dir = self.temporary_dir() / internal_id
        job_dir.mkdir(parents=True, exist_ok=False)
        destination = job_dir / f"{internal_id}{ext}"

        try:
            file.save(destination)
        except OSError:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise FileValidationError("INVALID_FILE", "The upload could not be saved.")

        try:
            size = destination.stat().st_size
        except OSError:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise FileValidationError("INVALID_FILE", "The upload could not be read.")

        if size == 0:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise FileValidationError("INVALID_FILE", "The uploaded file is empty.")

        max_size = current_app.config["MAX_CONTENT_LENGTH"]
        if size > max_size:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise FileValidationError(
                "FILE_TOO_LARGE",
                f"File exceeds the {max_size // (1024 * 1024)} MB limit.",
            )

        # Content validation and MIME assignment by extension family.
        if ext == ".pdf":
            ok, message = validate_pdf_file(destination)
            if not ok:
                shutil.rmtree(job_dir, ignore_errors=True)
                raise FileValidationError("INVALID_FILE", message)
            mime = "application/pdf"
        elif ext in {".png", ".jpg", ".jpeg"}:
            ok, message = validate_image_file(destination)
            if not ok:
                shutil.rmtree(job_dir, ignore_errors=True)
                raise FileValidationError("UNSUPPORTED_FORMAT", message)
            mime = "image/png" if ext == ".png" else "image/jpeg"
        elif ext in OOXML_MIME:
            ok, message = validate_ooxml_file(destination)
            if not ok:
                shutil.rmtree(job_dir, ignore_errors=True)
                raise FileValidationError("UNSUPPORTED_FORMAT", message)
            mime = OOXML_MIME[ext]
        elif ext in OLE_MIME:
            ok, message = validate_ole_file(destination)
            if not ok:
                shutil.rmtree(job_dir, ignore_errors=True)
                raise FileValidationError("UNSUPPORTED_FORMAT", message)
            mime = OLE_MIME[ext]
        elif ext in HTML_EXTENSIONS:
            ok, message = validate_html_file(destination)
            if not ok:
                shutil.rmtree(job_dir, ignore_errors=True)
                raise FileValidationError("UNSUPPORTED_FORMAT", message)
            mime = "text/html"
        else:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise FileValidationError("UNSUPPORTED_FORMAT", f"Unsupported type: {ext}.")

        now = datetime.now(timezone.utc)
        retention = current_app.config["FILE_RETENTION_SECONDS"]
        expires_at = now + timedelta(seconds=retention)

        meta = {
            "internal_id": internal_id,
            "original_filename": file.filename,
            "display_filename": display,
            "filename": destination.name,
            "extension": ext,
            "mime_type": mime,
            "size_bytes": size,
            "tool": tool,
            "uploaded_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        try:
            (job_dir / "meta.json").write_text(json.dumps(meta))
        except OSError:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise FileValidationError("INVALID_FILE", "The upload metadata could not be stored.")

        return StoredFile(
            internal_id=internal_id,
            original_filename=file.filename,
            display_filename=display,
            extension=ext,
            mime_type=mime,
            size_bytes=size,
            storage_path=destination,
            tool=tool,
            uploaded_at=now,
            expires_at=expires_at,
        )

    def get(self, internal_id: str) -> StoredFile | None:
        if not internal_id or "/" in internal_id or "\\" in internal_id or ".." in internal_id:
            return None
        job_dir = self.temporary_dir() / internal_id
        meta_path = job_dir / "meta.json"
        if not meta_path.is_file():
            return None
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        file_path = job_dir / meta.get("filename", "")
        if not file_path.is_file():
            return None
        try:
            return StoredFile(
                internal_id=meta["internal_id"],
                original_filename=meta["original_filename"],
                display_filename=meta["display_filename"],
                extension=meta["extension"],
                mime_type=meta["mime_type"],
                size_bytes=int(meta["size_bytes"]),
                storage_path=file_path,
                tool=meta["tool"],
                uploaded_at=datetime.fromisoformat(meta["uploaded_at"]),
                expires_at=datetime.fromisoformat(meta["expires_at"]),
            )
        except (KeyError, ValueError):
            return None

    def delete(self, stored: StoredFile) -> None:
        try:
            parent = stored.storage_path.parent
            if parent.is_dir() and parent.name == stored.internal_id:
                shutil.rmtree(parent, ignore_errors=True)
            elif stored.storage_path.exists():
                stored.storage_path.unlink(missing_ok=True)
        except OSError:
            log.exception("Failed to delete stored file %s", stored.internal_id)
