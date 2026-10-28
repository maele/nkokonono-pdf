"""Processing job record.

Only metadata is persisted; uploaded document contents and extracted text
never enter the database.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.extensions import db

VALID_TRANSITIONS: dict[str, set[str]] = {
    "queued":     {"processing", "failed", "expired"},
    "processing": {"completed", "failed", "expired"},
    "completed":  {"expired"},
    "failed":     {"expired"},
    "expired":    set(),
}


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.String(64), primary_key=True)
    tool_name = db.Column(db.String(64), nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default="queued", index=True)

    file_ids = db.Column(db.Text, nullable=False)  # JSON list
    options = db.Column(db.Text, nullable=True)    # JSON object
    outputs = db.Column(db.Text, nullable=True)    # JSON list of {path, name, mime, size}

    error_code = db.Column(db.String(64), nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    input_size_bytes = db.Column(db.Integer, default=0, nullable=False)
    output_size_bytes = db.Column(db.Integer, default=0, nullable=False)
    processing_duration_ms = db.Column(db.Integer, default=0, nullable=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tool": self.tool_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "outputs": json.loads(self.outputs) if self.outputs else [],
            "error": (
                {"code": self.error_code, "message": self.error_message}
                if self.error_code else None
            ),
            "input_size_bytes": self.input_size_bytes,
            "output_size_bytes": self.output_size_bytes,
            "processing_duration_ms": self.processing_duration_ms,
        }

    def transition_to(self, new_status: str) -> None:
        allowed = VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(f"Illegal job transition: {self.status} → {new_status}")
        self.status = new_status
        if new_status == "processing" and self.started_at is None:
            self.started_at = datetime.now(timezone.utc)
        if new_status in {"completed", "failed"} and self.completed_at is None:
            self.completed_at = datetime.now(timezone.utc)
        if new_status == "expired":
            self.expires_at = datetime.now(timezone.utc)    