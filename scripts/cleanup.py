"""Scheduled cleanup job.

Run periodically (cron, systemd timer, or a queue worker):

    python -m scripts.cleanup
"""
from __future__ import annotations

import logging
import sys

from app import create_app
from app.services.cleanup_service import CleanupService

log = logging.getLogger("cleanup")


def main() -> int:
    app = create_app()
    with app.app_context():
        removed = CleanupService().run()
        log.info("Removed %d expired entries.", removed)
        print(f"Removed {removed} expired entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())