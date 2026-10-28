"""Per-IP concurrency and per-job timeout enforcement.

Concurrency is tracked in-process: for the current single-process deployment
this is correct; multi-worker deployments need Redis-backed counters (see
`RATELIMIT_STORAGE_URI`). The timeout uses POSIX `SIGALRM`, which only fires
in the main thread — in production (Gunicorn sync workers) that is exactly
where request handling runs. In threaded environments, the timeout is a
no-op and Gunicorn's `--timeout` is the hard ceiling.
"""
from __future__ import annotations

import signal
import threading
from collections import defaultdict
from pathlib import Path

from app.processors.base import BaseProcessor, ProcessorError
from app.services.file_service import StoredFile

_inflight_lock = threading.Lock()
_inflight: dict[str, int] = defaultdict(int)


def acquire_job_slot(client_ip: str, limit: int) -> bool:
    if limit <= 0:
        return True
    with _inflight_lock:
        if _inflight[client_ip] >= limit:
            return False
        _inflight[client_ip] += 1
        return True


def release_job_slot(client_ip: str) -> None:
    with _inflight_lock:
        if _inflight[client_ip] > 0:
            _inflight[client_ip] -= 1
        if _inflight[client_ip] == 0:
            _inflight.pop(client_ip, None)


def inflight_count() -> int:
    with _inflight_lock:
        return sum(_inflight.values())


def run_with_timeout(
    processor: BaseProcessor,
    inputs: list[StoredFile],
    options: dict,
    output_dir: Path,
    timeout_seconds: float,
):
    supports_sigalrm = hasattr(signal, "SIGALRM")
    in_main_thread = threading.current_thread() is threading.main_thread()
    if not supports_sigalrm or not in_main_thread or timeout_seconds <= 0:
        return processor.process(inputs, options, output_dir)

    def _raise(signum, frame):
        raise ProcessorError(
            "PROCESSING_TIMEOUT",
            f"Processing exceeded the {int(timeout_seconds)}s limit. "
            "Try a smaller file or fewer pages.",
        )

    previous = signal.signal(signal.SIGALRM, _raise)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        return processor.process(inputs, options, output_dir)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)