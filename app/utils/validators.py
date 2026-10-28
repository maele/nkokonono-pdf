from __future__ import annotations

from pathlib import Path

PDF_MAGIC = b"%PDF-"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"

# OOXML (docx/xlsx/pptx) files are ZIP containers.
ZIP_MAGIC = b"PK\x03\x04"
ZIP_MAGIC_EMPTY = b"PK\x05\x06"

# Legacy Office (doc/xls/ppt) are OLE2 compound files.
OLE_MAGIC = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"


def _read_header(path: Path, size: int = 1024) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.read(size)
    except OSError:
        return b""


def validate_pdf_file(path: Path) -> tuple[bool, str]:
    header = _read_header(path)
    if not header.startswith(PDF_MAGIC):
        return False, "The file does not appear to be a valid PDF (missing %PDF- signature)."
    try:
        if path.stat().st_size < 16:
            return False, "The PDF file is too small to be valid."
    except OSError:
        return False, "The PDF file could not be inspected."
    return True, ""


def validate_image_file(path: Path) -> tuple[bool, str]:
    header = _read_header(path)
    if header.startswith(PNG_MAGIC) or header.startswith(JPEG_MAGIC):
        return True, ""
    return False, "The image is not a supported PNG or JPEG file."


def validate_ooxml_file(path: Path) -> tuple[bool, str]:
    """Validate OOXML (.docx/.xlsx/.pptx) — ZIP containers."""
    header = _read_header(path, 8)
    if header.startswith(ZIP_MAGIC) or header.startswith(ZIP_MAGIC_EMPTY):
        return True, ""
    return False, "The file does not appear to be a valid OOXML document."


def validate_ole_file(path: Path) -> tuple[bool, str]:
    """Validate legacy OLE2 (.doc/.xls/.ppt) — compound file binary."""
    header = _read_header(path, 8)
    if header.startswith(OLE_MAGIC):
        return True, ""
    return False, "The file does not appear to be a valid legacy Office document."


def validate_html_file(path: Path) -> tuple[bool, str]:
    """HTML has no magic number; accept only if it looks like markup."""
    try:
        sample = path.read_bytes()[:2048].decode("utf-8", errors="ignore").lower()
    except OSError:
        return False, "The HTML file could not be read."
    if "<html" in sample or "<!doctype html" in sample or "<body" in sample:
        return True, ""
    return False, "The file does not appear to be a valid HTML document."


def parse_page_range(expression: str, total_pages: int) -> list[int]:
    if not expression or not expression.strip():
        raise ValueError("Page range is empty.")
    if total_pages < 1:
        raise ValueError("Document has no pages.")

    result: list[int] = []
    seen: set[int] = set()

    for raw_part in expression.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, _, end_s = part.partition("-")
            try:
                start = int(start_s)
                end = int(end_s)
            except ValueError:
                raise ValueError(f"Invalid page range segment: {part!r}")
            if start > end:
                raise ValueError(f"Invalid range (start > end): {part!r}")
            if start < 1 or end > total_pages:
                raise ValueError(f"Page range {part!r} is outside the document (1-{total_pages}).")
            for page in range(start, end + 1):
                if page not in seen:
                    result.append(page)
                    seen.add(page)
        else:
            try:
                page = int(part)
            except ValueError:
                raise ValueError(f"Invalid page number: {part!r}")
            if page < 1 or page > total_pages:
                raise ValueError(f"Page {page} is outside the document (1-{total_pages}).")
            if page not in seen:
                result.append(page)
                seen.add(page)

    if not result:
        raise ValueError("No pages selected.")
    return result
