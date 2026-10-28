"""Scheduled cleanup of expired uploads, outputs and job records."""
from __future__ import annotations

import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app

from app.extensions import db
from app.models.job import Job

log = logging.getLogger(__name__)


class CleanupService:
    def __init__(self, storage_root: str | Path | None = None) -> None:
        self._storage_root = Path(storage_root or current_app.config["STORAGE_ROOT"])

    def run(self) -> int:
        removed = 0
        removed += self._clean(self._storage_root / "temporary")
        removed += self._clean(self._storage_root / "output")
        removed += self._expire_jobs()
        return removed

    def _clean(self, directory: Path) -> int:
        if not directory.is_dir():
            return 0
        retention = current_app.config["FILE_RETENTION_SECONDS"]
        now = time.time()
        removed = 0
        for entry in directory.iterdir():
            try:
                mtime = entry.stat().st_mtime
            except OSError:
                continue
            if now - mtime < retention:
                continue
            try:
                shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
                removed += 1
            except OSError:
                log.exception("Cleanup failed for %s", entry)
        return removed

    def _expire_jobs(self) -> int:
        # SQLite stores naive datetimes; compare in naive UTC so this works
        # on both SQLite (dev) and Postgres (prod, with tz-aware columns).
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        expired = (
            Job.query.filter(Job.expires_at.isnot(None), Job.expires_at < now).all()
        )
        for job in expired:
            db.session.delete(job)
        if expired:
            db.session.commit()
        return len(expired)