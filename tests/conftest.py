from __future__ import annotations

import io
import shutil
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfWriter


@pytest.fixture()
def app(tmp_path):
    from app import create_app

    storage_root = tmp_path / "storage"
    app = create_app("testing")
    app.config.update(
        STORAGE_ROOT=str(storage_root),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        MAX_FILES_PER_JOB=10,
        FILE_RETENTION_SECONDS=3600,
    )
    (storage_root / "temporary").mkdir(parents=True, exist_ok=True)
    (storage_root / "output").mkdir(parents=True, exist_ok=True)
    yield app
    shutil.rmtree(storage_root, ignore_errors=True)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def valid_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture()
def valid_png_bytes() -> bytes:
    img = Image.new("RGB", (4, 4), (13, 148, 136))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def sample_pdf_path(tmp_path, valid_pdf_bytes) -> Path:
    path = tmp_path / "sample.pdf"
    path.write_bytes(valid_pdf_bytes)
    return path

@pytest.fixture()
def upload_and_run(client):
    """Upload one or more files and start a job. Returns the job-create response."""
    def run(tool, files_data, options=None):
        ids = []
        for name, data in files_data:
            r = client.post(
                f"/tools/{tool}/upload",
                data={"files": (io.BytesIO(data), name)},
                content_type="multipart/form-data",
            )
            assert r.status_code == 201, r.data
            ids.append(r.get_json()["files"][0]["id"])
        return client.post(
            "/api/jobs",
            json={"tool": tool, "file_ids": ids, "options": options or {}},
        )
    return run