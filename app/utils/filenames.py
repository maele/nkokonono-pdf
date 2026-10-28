"""Filename sanitisation and internal identifier helpers.

The user-supplied filename is only ever used for display. All filesystem
paths are derived from a cryptographically random internal ID.
"""
from __future__ import annotations

import re
import secrets
import unicodedata
from pathlib import Path

_SAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]+")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_MAX_FILENAME_LENGTH = 200


def sanitize_display_filename(name: str) -> str:
    """Return a safe display filename. Never used for filesystem paths."""
    if not name:
        return "untitled"
    name = unicodedata.normalize("NFKC", name)
    name = _CONTROL_CHARS_RE.sub("", name)
    name = Path(name).name  # strip any directory components
    name = _SAFE_CHARS_RE.sub("_", name)
    name = name.strip("._- ")
    if not name:
        name = "untitled"

    if len(name) > _MAX_FILENAME_LENGTH:
        stem, dot, ext = name.rpartition(".")
        if dot and len(ext) <= 10:
            name = stem[: _MAX_FILENAME_LENGTH - len(ext) - 1] + "." + ext
        else:
            name = name[:_MAX_FILENAME_LENGTH]

    stem = name.split(".")[0].upper()
    if stem in _WINDOWS_RESERVED:
        name = "_" + name
    return name


def generate_internal_id() -> str:
    return secrets.token_urlsafe(24)


def get_safe_extension(name: str) -> str:
    ext = Path(name).suffix.lower()
    if not ext or len(ext) > 12:
        return ""
    return ext