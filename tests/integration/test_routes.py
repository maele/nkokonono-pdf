import io


def test_index_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Nkokonono ea PDF" in response.data


def test_tool_directory_lists_tools(client):
    response = client.get("/tools")
    assert response.status_code == 200
    assert b"Merge PDF" in response.data
    assert b"Split PDF" in response.data


def test_tool_page_renders(client):
    response = client.get("/tools/merge-pdf")
    assert response.status_code == 200
    assert b"Merge PDF" in response.data
    assert b"data-process-btn" in response.data


def test_unknown_tool_returns_404(client):
    response = client.get("/tools/does-not-exist")
    assert response.status_code == 404


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_upload_rejects_unknown_content(client):
    data = {"files": (io.BytesIO(b"not really a pdf"), "fake.pdf")}
    response = client.post(
        "/tools/merge-pdf/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "INVALID_FILE"


def test_upload_rejects_unsupported_extension(client, valid_png_bytes):
    # merge-pdf only accepts .pdf
    data = {"files": (io.BytesIO(valid_png_bytes), "image.png")}
    response = client.post(
        "/tools/merge-pdf/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "UNSUPPORTED_FORMAT"


def test_upload_accepts_valid_pdf(client, valid_pdf_bytes):
    data = {"files": (io.BytesIO(valid_pdf_bytes), "sample.pdf")}
    response = client.post(
        "/tools/merge-pdf/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    body = response.get_json()
    assert len(body["files"]) == 1
    assert body["files"][0]["mime"] == "application/pdf"
    assert body["files"][0]["size"] > 0


def test_upload_rejects_multiple_files_for_single_input_tool(client, valid_pdf_bytes):
    data = {
        "files": [
            (io.BytesIO(valid_pdf_bytes), "a.pdf"),
            (io.BytesIO(valid_pdf_bytes), "b.pdf"),
        ]
    }
    response = client.post(
        "/tools/pdf-to-images/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_FILE"


def test_upload_accepts_images_for_images_to_pdf(client, valid_png_bytes):
    data = {"files": (io.BytesIO(valid_png_bytes), "photo.png")}
    response = client.post(
        "/tools/images-to-pdf/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    assert response.get_json()["files"][0]["mime"] == "image/png"