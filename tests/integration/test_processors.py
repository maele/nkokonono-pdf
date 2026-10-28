"""End-to-end tests for every Phase 2 processor."""
from __future__ import annotations

import io

from PIL import Image
from pypdf import PdfReader, PdfWriter


def _multi_page_pdf(n: int = 3) -> bytes:
    writer = PdfWriter()
    for _ in range(n):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ---------- merge ----------

def test_merge_two_pdfs(upload_and_run, client, valid_pdf_bytes):
    r = upload_and_run("merge-pdf", [("a.pdf", valid_pdf_bytes), ("b.pdf", valid_pdf_bytes)])
    assert r.status_code == 200, r.data
    job = r.get_json()
    assert job["status"] == "completed", job
    assert len(job["outputs"]) == 1

    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert dl.status_code == 200
    merged = PdfReader(io.BytesIO(dl.data))
    assert len(merged.pages) == 2


def test_merge_requires_two_files(upload_and_run, valid_pdf_bytes):
    r = upload_and_run("merge-pdf", [("a.pdf", valid_pdf_bytes)])
    assert r.status_code == 200
    assert r.get_json()["status"] == "failed"
    assert r.get_json()["error"]["code"] == "INVALID_FILE"


# ---------- split ----------

def test_split_every_page(upload_and_run, client):
    r = upload_and_run("split-pdf", [("doc.pdf", _multi_page_pdf(3))], {"mode": "every"})
    job = r.get_json()
    assert job["status"] == "completed", job
    assert job["outputs"][0]["mime"] == "application/zip"
    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert dl.status_code == 200
    assert dl.data[:2] == b"PK"


def test_split_ranges(upload_and_run, client):
    r = upload_and_run("split-pdf", [("doc.pdf", _multi_page_pdf(6))],
                       {"mode": "ranges", "ranges": "1-2,4"})
    job = r.get_json()
    assert job["status"] == "completed", job


def test_split_rejects_bad_range(upload_and_run):
    r = upload_and_run("split-pdf", [("doc.pdf", _multi_page_pdf(3))],
                       {"mode": "ranges", "ranges": "5-10"})
    assert r.get_json()["status"] == "failed"
    assert r.get_json()["error"]["code"] == "INVALID_PAGE_RANGE"


# ---------- compress ----------

def test_compress_returns_pdf(upload_and_run, client):
    r = upload_and_run("compress-pdf", [("doc.pdf", _multi_page_pdf(2))], {"profile": "recommended"})
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    reader = PdfReader(io.BytesIO(dl.data))
    assert len(reader.pages) == 2


# ---------- rotate ----------

def test_rotate_all_pages(upload_and_run, client):
    r = upload_and_run("rotate-pdf", [("doc.pdf", _multi_page_pdf(2))], {"angle": 90})
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    reader = PdfReader(io.BytesIO(dl.data))
    assert len(reader.pages) == 2


def test_rotate_rejects_bad_angle(upload_and_run):
    r = upload_and_run("rotate-pdf", [("doc.pdf", _multi_page_pdf(2))], {"angle": 45})
    assert r.get_json()["status"] == "failed"


# ---------- extract ----------

def test_extract_pages(upload_and_run, client):
    r = upload_and_run("extract-pages", [("doc.pdf", _multi_page_pdf(5))], {"pages": "1,3,5"})
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert len(PdfReader(io.BytesIO(dl.data)).pages) == 3


# ---------- delete ----------

def test_delete_pages(upload_and_run, client):
    r = upload_and_run("delete-pages", [("doc.pdf", _multi_page_pdf(5))], {"pages": "2,4"})
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert len(PdfReader(io.BytesIO(dl.data)).pages) == 3


# ---------- organise ----------

def test_organise_reorders_and_rotates(upload_and_run, client):
    r = upload_and_run(
        "organise-pdf",
        [("doc.pdf", _multi_page_pdf(3))],
        {"order": "3,1,2", "rotations": "3:90"},
    )
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert len(PdfReader(io.BytesIO(dl.data)).pages) == 3


# ---------- images → PDF ----------

def test_images_to_pdf(upload_and_run, client, valid_png_bytes):
    r = upload_and_run(
        "images-to-pdf",
        [("a.png", valid_png_bytes), ("b.png", valid_png_bytes)],
        {"page_size": "a4"},
    )
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    assert len(PdfReader(io.BytesIO(dl.data)).pages) == 2


# ---------- PDF → images ----------

def test_pdf_to_images_png_zip(upload_and_run, client):
    r = upload_and_run("pdf-to-images", [("doc.pdf", _multi_page_pdf(2))],
                       {"format": "png", "dpi": 96})
    job = r.get_json()
    assert job["status"] == "completed", job
    assert job["outputs"][0]["mime"] == "application/zip"


def test_pdf_to_images_single_page(upload_and_run, client):
    r = upload_and_run("pdf-to-images", [("doc.pdf", _multi_page_pdf(1))],
                       {"format": "png", "dpi": 96})
    job = r.get_json()
    assert job["status"] == "completed", job
    assert job["outputs"][0]["mime"] == "image/png"


# ---------- protect / unlock ----------

def test_protect_and_unlock_round_trip(upload_and_run, client):
    r = upload_and_run("protect-pdf", [("doc.pdf", _multi_page_pdf(2))], {"password": "hunter2"})
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    protected_bytes = dl.data
    reader = PdfReader(io.BytesIO(protected_bytes))
    assert reader.is_encrypted
    assert reader.decrypt("hunter2")

    # Upload the protected PDF, then unlock it
    up = client.post(
        "/tools/unlock-pdf/upload",
        data={"files": (io.BytesIO(protected_bytes), "protected.pdf")},
        content_type="multipart/form-data",
    )
    fid = up.get_json()["files"][0]["id"]
    r = client.post("/api/jobs", json={"tool": "unlock-pdf", "file_ids": [fid],
                                        "options": {"password": "hunter2"}})
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    unlocked = PdfReader(io.BytesIO(dl.data))
    assert not unlocked.is_encrypted


def test_unlock_wrong_password(upload_and_run, client):
    r = upload_and_run("protect-pdf", [("doc.pdf", _multi_page_pdf(1))], {"password": "secret1"})
    job = r.get_json()
    dl = client.get(f"/api/jobs/{job['id']}/download")
    protected_bytes = dl.data

    up = client.post(
        "/tools/unlock-pdf/upload",
        data={"files": (io.BytesIO(protected_bytes), "protected.pdf")},
        content_type="multipart/form-data",
    )
    fid = up.get_json()["files"][0]["id"]
    r = client.post("/api/jobs", json={"tool": "unlock-pdf", "file_ids": [fid],
                                        "options": {"password": "wrong"}})
    body = r.get_json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "ENCRYPTED_PDF"


def test_protect_rejects_short_password(upload_and_run):
    r = upload_and_run("protect-pdf", [("doc.pdf", _multi_page_pdf(1))], {"password": "abc"})
    body = r.get_json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "INVALID_FILE"


# ---------- metadata ----------

def test_metadata_edit(upload_and_run, client):
    r = upload_and_run(
        "pdf-metadata",
        [("doc.pdf", _multi_page_pdf(1))],
        {"title": "Quarterly report", "author": "Finance"},
    )
    job = r.get_json()
    assert job["status"] == "completed", job
    dl = client.get(f"/api/jobs/{job['id']}/download")
    reader = PdfReader(io.BytesIO(dl.data))
    assert reader.metadata.get("/Title") == "Quarterly report"
    assert reader.metadata.get("/Author") == "Finance"


def test_metadata_clear(upload_and_run, client):
    r = upload_and_run("pdf-metadata", [("doc.pdf", _multi_page_pdf(1))], {"clear": True})
    job = r.get_json()
    assert job["status"] == "completed", job


# ---------- job lifecycle ----------

def test_download_rejects_unknown_job(client):
    assert client.get("/api/jobs/does-not-exist/download").status_code == 404


def test_download_rejects_failed_job(upload_and_run, client):
    # A single PDF is not enough for merge; the job fails during validation.
    r = upload_and_run("merge-pdf", [("a.pdf", _multi_page_pdf(1))])
    job = r.get_json()
    assert job["status"] == "failed", job
    assert job["error"]["code"] == "INVALID_FILE"
    assert client.get(f"/api/jobs/{job['id']}/download").status_code == 409