"""Create and run processing jobs synchronously.

Background workers replace the synchronous call in Phase 4; the job model
and status transitions stay the same.
"""
from __future__ import annotations

import json
import logging
import secrets
import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import current_app

from app.extensions import db
from app.models.job import Job
from app.processors.base import BaseProcessor, ProcessorError
from app.processors.registry import get_processor
from app.services.file_service import FileService, StoredFile
from app.utils.resilience import (
    acquire_job_slot,
    release_job_slot,
    run_with_timeout,
)

log = logging.getLogger(__name__)


class JobError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _as_aware_utc(dt: datetime | None) -> datetime | None:
    """SQLite strips tzinfo; treat naive values as UTC."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class JobService:
    def __init__(self) -> None:
        self.file_service = FileService()

    # ---------------------------------------------------------------- create

    def create_job(
        self,
        tool: str,
        file_ids: list[str],
        options: dict,
        client_ip: str | None = None,
    ) -> Job:
        processor = get_processor(tool)
        if processor is None:
            raise JobError("UNSUPPORTED_TOOL", f"No processor is registered for '{tool}'.")
        if not isinstance(file_ids, list) or not file_ids:
            raise JobError("INVALID_FILE", "No input files were provided.")

        limit = 0
        if client_ip:
            limit = current_app.config["MAX_CONCURRENT_JOBS_PER_IP"]
            if not acquire_job_slot(client_ip, limit):
                raise JobError(
                    "RATE_LIMIT_EXCEEDED",
                    f"Too many concurrent jobs ({limit}) from this address. "
                    "Wait for the current jobs to finish.",
                )

        try:
            inputs: list[StoredFile] = []
            for fid in file_ids:
                if not isinstance(fid, str):
                    raise JobError("INVALID_FILE", "File references must be strings.")
                stored = self.file_service.get(fid)
                if stored is None:
                    raise JobError(
                        "INVALID_FILE",
                        f"File reference '{fid}' is unknown or has expired.",
                    )
                inputs.append(stored)

            job = Job(
                id=secrets.token_urlsafe(18),
                tool_name=tool,
                status="queued",
                file_ids=json.dumps(file_ids),
                options=json.dumps(options or {}),
                input_size_bytes=sum(i.size_bytes for i in inputs),
            )
            db.session.add(job)
            db.session.commit()

            self._run(job, processor, inputs, options or {})
            db.session.refresh(job)
            return job
        finally:
            if client_ip and limit > 0:
                release_job_slot(client_ip)

    # ------------------------------------------------------------------ read

    def get_job(self, job_id: str) -> Job | None:
        return db.session.get(Job, job_id)

    def is_expired(self, job: Job) -> bool:
        expires = _as_aware_utc(job.expires_at)
        return expires is not None and expires < datetime.now(timezone.utc)

    # --------------------------------------------------------------- internal

    def _run(
        self,
        job: Job,
        processor: BaseProcessor,
        inputs: list[StoredFile],
        options: dict,
    ) -> None:
        job.transition_to("processing")
        db.session.commit()

        started = time.monotonic()
        output_dir = Path(current_app.config["STORAGE_ROOT"]) / "output" / job.id
        output_dir.mkdir(parents=True, exist_ok=True)
        timeout = current_app.config["JOB_TIMEOUT_SECONDS"]

        try:
            processor.validate(inputs, options)
            outputs = run_with_timeout(processor, inputs, options, output_dir, timeout)
            if not outputs:
                raise ProcessorError(
                    "OUTPUT_VALIDATION_FAILED",
                    "The processor produced no output.",
                )
            for out in outputs:
                processor.validate_output(out)

            output_data = [
                {
                    "path": str(out.path),
                    "name": out.display_name,
                    "mime": out.mime_type,
                    "size": out.path.stat().st_size,
                    "notes": out.notes,
                }
                for out in outputs
            ]

            retention = current_app.config["FILE_RETENTION_SECONDS"]
            job.transition_to("completed")
            job.expires_at = job.completed_at + timedelta(seconds=retention)
            job.outputs = json.dumps(output_data)
            job.output_size_bytes = sum(item["size"] for item in output_data)
        except ProcessorError as exc:
            self._fail(job, exc.code, exc.message, output_dir)
        except Exception:
            log.exception(
                "Job failed unexpectedly",
                extra={"job_id": job.id, "tool": job.tool_name},
            )
            self._fail(
                job,
                "PROCESSING_FAILED",
                "An unexpected error occurred while processing the document.",
                output_dir,
            )
        finally:
            job.processing_duration_ms = int((time.monotonic() - started) * 1000)
            db.session.commit()
            log.info(
                "Job finished",
                extra={
                    "job_id": job.id,
                    "tool": job.tool_name,
                    "status": job.status,
                    "duration_ms": job.processing_duration_ms,
                    "code": job.error_code,
                },
            )

    def _fail(
        self,
        job: Job,
        code: str,
        message: str,
        output_dir: Path,
    ) -> None:
        try:
            job.transition_to("failed")
        except ValueError:
            # The job may already be in a terminal state; force the marker
            # so the UI does not show a stale success.
            job.status = "failed"
        job.error_code = code
        job.error_message = message
        shutil.rmtree(output_dir, ignore_errors=True)
