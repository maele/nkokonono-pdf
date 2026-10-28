from __future__ import annotations

import importlib
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSpec:
    slug: str
    title: str
    summary: str
    category: str
    accepts: tuple[str, ...]
    multiple: bool = False
    implemented: bool = False
    icon: str = "file-earmark"
    requires: tuple[str, ...] = ()  # "python:module" or "binary:name"


def is_available(spec: ToolSpec) -> tuple[bool, str | None]:
    """Return (available, reason). Reason is None if available."""
    if not spec.implemented:
        return False, "This tool is not yet implemented."
    for req in spec.requires:
        kind, _, name = req.partition(":")
        if kind == "python":
            try:
                importlib.import_module(name)
            except Exception:
                return False, f"Required Python package '{name}' is not installed."
        elif kind == "binary":
            if shutil.which(name) is None:
                return False, f"Required system binary '{name}' is not installed."
    return True, None


TOOLS: tuple[ToolSpec, ...] = (
    # --- Phase 2 (all implemented, no extra deps) ---
    ToolSpec("merge-pdf", "Merge PDF", "Combine multiple PDFs into a single document in your chosen order.", "Organise PDF", (".pdf",), multiple=True, implemented=True, icon="files"),
    ToolSpec("split-pdf", "Split PDF", "Extract page ranges or split a PDF into separate documents.", "Organise PDF", (".pdf",), implemented=True, icon="scissors"),
    ToolSpec("compress-pdf", "Compress PDF", "Reduce PDF file size while keeping readable quality.", "Optimise PDF", (".pdf",), implemented=True, icon="arrows-collapse"),
    ToolSpec("organise-pdf", "Organise PDF", "Reorder, duplicate, rotate and remove pages interactively with a live preview.", "Organise PDF", (".pdf",), implemented=True, icon="grid"),
    ToolSpec("extract-pages", "Extract pages", "Export selected pages as a new PDF.", "Organise PDF", (".pdf",), implemented=True, icon="box-arrow-up-right"),
    ToolSpec("rotate-pdf", "Rotate PDF", "Rotate all or selected pages in 90-degree steps.", "Edit PDF", (".pdf",), implemented=True, icon="arrow-repeat"),
    ToolSpec("delete-pages", "Delete pages", "Remove selected pages from a PDF.", "Edit PDF", (".pdf",), implemented=True, icon="trash"),
    ToolSpec("pdf-to-images", "PDF to images", "Export PDF pages as PNG or JPEG images.", "Convert from PDF", (".pdf",), implemented=True, icon="image"),
    ToolSpec("images-to-pdf", "Images to PDF", "Convert images into a single PDF document.", "Convert to PDF", (".png", ".jpg", ".jpeg"), multiple=True, implemented=True, icon="file-earmark-image"),
    ToolSpec("protect-pdf", "Protect PDF", "Encrypt a PDF with an opening password.", "Secure PDF", (".pdf",), implemented=True, icon="lock"),
    ToolSpec("unlock-pdf", "Unlock PDF", "Remove supported encryption when you supply the password.", "Secure PDF", (".pdf",), implemented=True, icon="unlock"),
    ToolSpec("pdf-metadata", "PDF metadata", "View and edit document metadata.", "Edit PDF", (".pdf",), implemented=True, icon="tags"),

    # --- Phase 4 ---
    ToolSpec("watermark-pdf", "Watermark PDF", "Stamp text across every page.", "Edit PDF", (".pdf",), implemented=True, icon="droplet",
             requires=("python:reportlab",)),
    ToolSpec("page-numbers", "Add page numbers", "Number every page.", "Edit PDF", (".pdf",), implemented=True, icon="hash",
             requires=("python:reportlab",)),
    ToolSpec("headers-footers", "Headers & footers", "Add custom text to the top and bottom of every page.", "Edit PDF", (".pdf",), implemented=True, icon="layout-text-window",
             requires=("python:reportlab",)),
    ToolSpec("repair-pdf", "Repair PDF", "Attempt to recover a damaged PDF.", "Optimise PDF", (".pdf",), implemented=True, icon="tools"),
    ToolSpec("compare-pdf", "Compare PDFs", "Produce a text report of differences between two PDFs.", "Edit PDF", (".pdf",), multiple=True, implemented=True, icon="diff"),
    ToolSpec("word-to-pdf", "Word to PDF", "Convert Word documents to PDF.", "Convert to PDF", (".docx", ".doc"), implemented=True, icon="file-earmark-word",
             requires=("binary:libreoffice",)),
    ToolSpec("excel-to-pdf", "Excel to PDF", "Convert Excel spreadsheets to PDF.", "Convert to PDF", (".xlsx", ".xls"), implemented=True, icon="file-earmark-excel",
             requires=("binary:libreoffice",)),
    ToolSpec("ppt-to-pdf", "PowerPoint to PDF", "Convert PowerPoint presentations to PDF.", "Convert to PDF", (".pptx", ".ppt"), implemented=True, icon="file-earmark-slides",
             requires=("binary:libreoffice",)),
    ToolSpec("pdf-to-word", "PDF to Word", "Convert a text-based PDF to a Word document.", "Convert from PDF", (".pdf",), implemented=True, icon="file-earmark-word",
             requires=("python:pdf2docx",)),
    ToolSpec("pdf-to-excel", "PDF to Excel", "Extract tables from a text-based PDF into a spreadsheet.", "Convert from PDF", (".pdf",), implemented=True, icon="file-earmark-excel",
             requires=("python:pdfplumber",)),
    ToolSpec("pdf-to-ppt", "PDF to PowerPoint", "Convert PDF pages into image-backed slides.", "Convert from PDF", (".pdf",), implemented=True, icon="file-earmark-slides",
             requires=("python:pptx",)),
    ToolSpec("html-to-pdf", "HTML to PDF", "Render an HTML file as a PDF.", "Convert to PDF", (".html", ".htm"), implemented=True, icon="filetype-html",
             requires=("python:weasyprint",)),
    ToolSpec("ocr-pdf", "OCR PDF", "Add a searchable text layer to a scanned PDF.", "Optimise PDF", (".pdf",), implemented=True, icon="textarea-t",
             requires=("binary:ocrmypdf",)),
)

TOOLS_BY_SLUG: dict[str, ToolSpec] = {t.slug: t for t in TOOLS}

CATEGORIES: tuple[str, ...] = (
    "Organise PDF", "Convert to PDF", "Convert from PDF",
    "Optimise PDF", "Edit PDF", "Secure PDF",
)

_POPULAR_CANDIDATES: tuple[str, ...] = (
    "merge-pdf",
    "compress-pdf",
    "split-pdf",
    "pdf-to-word",
    "images-to-pdf",
    "protect-pdf",
)

# Filtered so a refactor (renaming/removing a tool) cannot break the landing page.
POPULAR_SLUGS: tuple[str, ...] = tuple(
    s for s in _POPULAR_CANDIDATES if s in TOOLS_BY_SLUG
)
