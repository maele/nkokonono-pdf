"""Tool pages and the upload endpoint used by the shared upload component."""
from __future__ import annotations

import logging

import fitz
from flask import Blueprint, abort, current_app, jsonify, make_response, render_template, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from app.extensions import limiter
from app.services.file_service import FileService, FileValidationError
from app.tools.registry import CATEGORIES, TOOLS_BY_SLUG
from app.utils.filenames import get_safe_extension, sanitize_display_filename

log = logging.getLogger(__name__)
bp = Blueprint("tools", __name__, url_prefix="/tools")


from app.tools.registry import CATEGORIES, TOOLS_BY_SLUG, is_available


@bp.get("/<tool_name>")
def tool_page(tool_name: str):
    spec = TOOLS_BY_SLUG.get(tool_name)
    if spec is None:
        abort(404)
    available, reason = is_available(spec)
    return render_template(
        "tools/tool_page.html",
        tool=spec,
        categories=CATEGORIES,
        tool_available=available,
        tool_unavailable_reason=reason,
    )


@bp.post("/<tool_name>/upload")
@limiter.limit(lambda: current_app.config["RATELIMIT_UPLOAD"])
def upload(tool_name: str):
    spec = TOOLS_BY_SLUG.get(tool_name)
    if spec is None:
        abort(404)

    try:
        files = request.files.getlist("files")
    except RequestEntityTooLarge:
        return _error("FILE_TOO_LARGE", "The upload exceeds the configured limit.", 413)

    real_files = [f for f in files if f and f.filename]
    if not real_files:
        return _error("INVALID_FILE", "No files were provided.", 400)

    if not spec.multiple and len(real_files) > 1:
        return _error("INVALID_FILE", f"{spec.title} accepts a single file.", 400)

    max_files = 20  # mirror config; MAX_CONTENT_LENGTH caps total bytes per request
    if len(real_files) > max_files:
        return _error("INVALID_FILE", f"At most {max_files} files may be uploaded at once.", 400)

    service = FileService()
    stored = []
    try:
        for file in real_files:
            ext = get_safe_extension(sanitize_display_filename(file.filename))
            if ext not in spec.accepts:
                raise FileValidationError(
                    "UNSUPPORTED_FORMAT",
                    f"{spec.title} does not accept '{ext or 'unknown'}' files. "
                    f"Supported: {', '.join(spec.accepts)}.",
                )
            stored.append(service.store_upload(file, tool=spec.slug))
    except FileValidationError as exc:
        # Roll back any files stored before the failure so nothing is orphaned.
        for item in stored:
            service.delete(item)
        return _error(exc.code, exc.message, 400)

    payload = [
        {
            "id": s.internal_id,
            "name": s.display_filename,
            "size": s.size_bytes,
            "mime": s.mime_type,
            "expires_at": s.expires_at.isoformat(),
        }
        for s in stored
    ]
    return jsonify({"files": payload}), 201


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status

# --- Organise PDF preview endpoints ----------------------------------------

def _load_preview_file(tool_name: str, file_id: str):
    """Resolve a stored PDF for preview, or abort 404.

    The file must have been uploaded via the same tool URL to prevent
    cross-tool access (e.g. previewing a merge upload via an organise URL).
    """
    spec = TOOLS_BY_SLUG.get(tool_name)
    if spec is None or ".pdf" not in spec.accepts:
        abort(404)
    stored = FileService().get(file_id)
    if stored is None or stored.tool != tool_name or stored.extension != ".pdf":
        abort(404)
    return stored


@bp.get("/<tool_name>/preview/<file_id>/info")
def preview_info(tool_name: str, file_id: str):
    stored = _load_preview_file(tool_name, file_id)
    try:
        doc = fitz.open(str(stored.storage_path))
        count = doc.page_count
        doc.close()
    except Exception:
        abort(404)
    return jsonify({
        "file_id": file_id,
        "page_count": count,
        "display_name": stored.display_filename,
    })


@bp.get("/<tool_name>/preview/<file_id>/page-<int:page_number>.png")
def preview_page(tool_name: str, file_id: str, page_number: int):
    stored = _load_preview_file(tool_name, file_id)

    try:
        doc = fitz.open(str(stored.storage_path))
    except Exception:
        abort(404)

    try:
        if page_number < 1 or page_number > doc.page_count:
            abort(404)
        page = doc.load_page(page_number - 1)
        target = 240.0
        rect = page.rect
        scale = target / max(rect.width, rect.height)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        png_bytes = pix.tobytes("png")
    except HTTPException:
        raise
    except Exception:
        abort(404)
    finally:
        doc.close()

    response = make_response(png_bytes)
    response.headers["Content-Type"] = "image/png"
    response.headers["Cache-Control"] = "private, max-age=300"
    return response
