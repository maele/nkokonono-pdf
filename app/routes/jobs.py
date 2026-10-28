"""Job creation, polling and authorised download."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile

from flask import Blueprint, current_app, jsonify, request, send_file

from app.extensions import limiter
from app.services.job_service import JobError, JobService

bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")


@bp.post("")
@limiter.limit(lambda: current_app.config["RATELIMIT_JOB_CREATE"])
def create_job():
    payload = request.get_json(silent=True) or {}
    tool = payload.get("tool")
    file_ids = payload.get("file_ids") or []
    options = payload.get("options") or {}

    if not isinstance(tool, str) or not tool:
        return _error("INVALID_REQUEST", "Missing 'tool'.", 400)
    if not isinstance(file_ids, list):
        return _error("INVALID_REQUEST", "'file_ids' must be a list.", 400)
    if not isinstance(options, dict):
        return _error("INVALID_REQUEST", "'options' must be an object.", 400)

    try:
        job = JobService().create_job(
            tool,
            file_ids,
            options,
            client_ip=request.remote_addr or "unknown",
        )
    except JobError as exc:
        return _error(exc.code, exc.message, 400)

    return jsonify(job.to_dict()), 200


@bp.get("/<job_id>")
def get_job(job_id: str):
    service = JobService()
    job = service.get_job(job_id)
    if job is None:
        return _error("NOT_FOUND", "Job not found.", 404)
    if service.is_expired(job):
        return _error("JOB_EXPIRED", "This job has expired.", 410)
    return jsonify(job.to_dict())


@bp.get("/<job_id>/download")
def download(job_id: str):
    service = JobService()
    job = service.get_job(job_id)
    if job is None:
        return _error("NOT_FOUND", "Job not found.", 404)
    if job.status != "completed":
        return _error("JOB_NOT_READY", "The job has not completed successfully.", 409)
    if service.is_expired(job):
        return _error("JOB_EXPIRED", "This job has expired.", 410)

    outputs = json.loads(job.outputs or "[]")
    if not outputs:
        return _error("NOT_FOUND", "No outputs are available.", 404)

    # Resolve every output path and confirm it lives inside the output root.
    # Using resolve() also defends against symlink escapes.
    output_root = (Path(current_app.config["STORAGE_ROOT"]) / "output").resolve()
    resolved: list[tuple[Path, dict]] = []
    for item in outputs:
        candidate = Path(item["path"]).resolve()
        if not candidate.is_file():
            return _error("JOB_EXPIRED", "The output is no longer available.", 410)
        if not candidate.is_relative_to(output_root):
            return _error("FORBIDDEN", "Invalid output path.", 403)
        resolved.append((candidate, item))

    # Single output: stream it directly with the correct MIME and name.
    if len(resolved) == 1:
        path, item = resolved[0]
        return send_file(
            path,
            mimetype=item["mime"],
            as_attachment=True,
            download_name=item["name"],
        )

    # Multiple outputs: package them into a ZIP of already-validated paths.
    tmp = NamedTemporaryFile(suffix=".zip", delete=False)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, item in resolved:
                zf.write(path, arcname=item["name"])
    finally:
        tmp.close()
    return send_file(
        tmp.name,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{job.tool_name}-{job.id[:8]}.zip",
    )


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status