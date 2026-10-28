"""Log formatters: JSON for production, human-readable for development."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

_EXTRA_FIELDS = ("job_id", "tool", "duration_ms", "status", "client_ip", "code")


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for name in _EXTRA_FIELDS:
            value = getattr(record, name, None)
            if value is not None:
                payload[name] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app) -> None:
    """Replace Flask's default handler with one using the configured format."""
    level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)
    handler = logging.StreamHandler()
    if app.config.get("LOG_FORMAT") == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s")
        )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)