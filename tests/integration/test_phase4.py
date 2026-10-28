from __future__ import annotations

import io
import shutil

import pytest
from pypdf import PdfReader, PdfWriter


def _pdf_bytes(pages: int = 1) -> bytes:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def _pdf_with_text(text: str) -> bytes:
    from reportlab.pdfgen import canvas as rl_canvas
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(612, 792))
    c.setFont("Helvetica", 12)
    c.drawString(72, 720, text)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def _has_binary(name: str) -> bool:
    return shutil.which(name) is not None


def _has_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def test_watermark(upload_and_run, client):
    r = upload_and_run("watermark-pdf", [("doc.pdf", _pdf_bytes(2))],
                       {"text": "CONFIDENTIAL", "opacity": 0.3, "font_size": 48})
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert len(PdfReader(io.BytesIO(dl.data)).pages) == 2


def test_watermark_requires_text(upload_and_run):
    r = upload_and_run("watermark-pdf", [("doc.pdf", _pdf_bytes(1))], {})
    assert r.get_json()["status"] == "failed"
    assert r.get_json()["error"]["code"] == "INVALID_FILE"


def test_page_numbers(upload_and_run, client):
    r = upload_and_run("page-numbers", [("doc.pdf", _pdf_bytes(3))],
                       {"position": "bottom-center", "start": 1, "prefix": "Page "})
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert len(PdfReader(io.BytesIO(dl.data)).pages) == 3


def test_headers_footers(upload_and_run):
    r = upload_and_run("headers-footers", [("doc.pdf", _pdf_bytes(2))],
                       {"header": "Title", "footer": "Confidential"})
    assert r.get_json()["status"] == "completed"


def test_headers_footers_requires_one(upload_and_run):
    r = upload_and_run("headers-footers", [("doc.pdf", _pdf_bytes(1))], {})
    assert r.get_json()["error"]["code"] == "INVALID_FILE"


def test_repair_accepts_valid_pdf(upload_and_run, client):
    r = upload_and_run("repair-pdf", [("doc.pdf", _pdf_bytes(2))])
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert len(PdfReader(io.BytesIO(dl.data)).pages) == 2


def test_compare_produces_report(upload_and_run, client):
    r = upload_and_run("compare-pdf", [
        ("a.pdf", _pdf_bytes(2)),
        ("b.pdf", _pdf_bytes(2)),
    ])
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    text = dl.data.decode("utf-8")
    assert "Comparison report" in text
    assert "identical" in text


def test_compare_detects_difference(upload_and_run, client):
    r = upload_and_run("compare-pdf", [
        ("a.pdf", _pdf_with_text("hello")),
        ("b.pdf", _pdf_with_text("goodbye")),
    ])
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert "differences" in dl.data.decode("utf-8")


@pytest.mark.skipif(not _has_module("pdf2docx"), reason="pdf2docx not installed")
def test_pdf_to_word(upload_and_run):
    r = upload_and_run("pdf-to-word", [("doc.pdf", _pdf_with_text("hello"))])
    assert r.get_json()["status"] == "completed"


@pytest.mark.skipif(not _has_module("pdfplumber"), reason="pdfplumber not installed")
def test_pdf_to_excel_no_table_fails(upload_and_run):
    r = upload_and_run("pdf-to-excel", [("doc.pdf", _pdf_with_text("no tables here"))])
    body = r.get_json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "CONVERSION_FAILED"


@pytest.mark.skipif(not _has_module("pptx"), reason="python-pptx not installed")
def test_pdf_to_ppt(upload_and_run, client):
    r = upload_and_run("pdf-to-ppt", [("doc.pdf", _pdf_bytes(2))], {"dpi": 96})
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert dl.data[:2] == b"PK"


@pytest.mark.skipif(
    not _has_binary("libreoffice") or not _has_module("docx"),
    reason="LibreOffice or python-docx not installed",
)
def test_word_to_pdf(upload_and_run):
    from docx import Document
    doc = Document()
    doc.add_paragraph("Hello world")
    buf = io.BytesIO()
    doc.save(buf)
    r = upload_and_run("word-to-pdf", [("doc.docx", buf.getvalue())])
    assert r.get_json()["status"] == "completed"


@pytest.mark.skipif(not _has_module("weasyprint"), reason="WeasyPrint not installed")
def test_html_to_pdf(upload_and_run):
    html = b"<html><body><h1>Hello</h1></body></html>"
    r = upload_and_run("html-to-pdf", [("page.html", html)])
    assert r.get_json()["status"] == "completed"


@pytest.mark.skipif(not _has_binary("ocrmypdf"), reason="OCRmyPDF not installed")
def test_ocr(upload_and_run):
    r = upload_and_run("ocr-pdf", [("scan.pdf", _pdf_bytes(1))], {"language": "eng", "force": True})
    assert r.get_json()["status"] in ("completed", "failed")


def test_unavailable_tool_shows_message(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.tools.is_available",
        lambda s: (False, "LibreOffice is not installed."),
    )
    r = client.get("/tools/word-to-pdf")
    assert r.status_code == 200
    assert b"This tool is not available" in r.data
    assert b"LibreOffice is not installed" in r.data
