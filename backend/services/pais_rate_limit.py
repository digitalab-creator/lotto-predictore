"""One gate for every pais.co.il request.

Two processes must not talk to Mifal HaPais at the same time, and they must
not keep separate sleep timers. The shared lock file and next-allowed stamp
live on the shared volume so backend, cron-triggered sync, and scripts
count the same seconds.
"""

from __future__ import annotations

import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config import (
    PAIS_ERROR_COOLDOWN_SECONDS,
    PAIS_GATE_DIR,
    PAIS_MIN_INTERVAL_SECONDS,
)
from logger import logger

_LOCK_NAME = "request.lock"
_NEXT_NAME = "next_allowed.txt"


def _paths(gate_dir: Path | None = None) -> tuple[Path, Path, Path]:
    root = Path(gate_dir) if gate_dir is not None else Path(PAIS_GATE_DIR)
    return root, root / _LOCK_NAME, root / _NEXT_NAME


def _read_next_allowed(stamp_path: Path) -> float:
    try:
        text = stamp_path.read_text(encoding="utf-8").strip()
        return float(text) if text else 0.0
    except (OSError, ValueError):
        return 0.0


def _write_next_allowed(stamp_path: Path, when: float) -> None:
    tmp = stamp_path.with_suffix(".tmp")
    tmp.write_text(f"{when:.6f}\n", encoding="utf-8")
    os.replace(tmp, stamp_path)


@contextmanager
def pais_request_slot(
    *,
    gate_dir: Path | None = None,
    min_interval: float | None = None,
) -> Iterator[None]:
    """Hold the global Pais lock for one HTTP call. Waits on the shared clock."""
    root, lock_path, stamp_path = _paths(gate_dir)
    interval = PAIS_MIN_INTERVAL_SECONDS if min_interval is None else float(min_interval)
    root.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            now = time.time()
            next_allowed = _read_next_allowed(stamp_path)
            wait = next_allowed - now
            if wait > 0:
                logger.info(
                    "Pais gate waiting on shared clock",
                    context={"wait_s": round(wait, 2), "pid": os.getpid()},
                )
                time.sleep(wait)
            yield
        finally:
            # Stamp after the call so the next process waits a full interval from now.
            _write_next_allowed(stamp_path, time.time() + interval)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def mark_pais_error_cooldown(
    *,
    gate_dir: Path | None = None,
    cooldown: float | None = None,
) -> None:
    """Push the shared next-allowed time out after an error page."""
    root, lock_path, stamp_path = _paths(gate_dir)
    cool = PAIS_ERROR_COOLDOWN_SECONDS if cooldown is None else float(cooldown)
    root.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            until = time.time() + cool
            current = _read_next_allowed(stamp_path)
            _write_next_allowed(stamp_path, max(current, until))
            logger.warning(
                "Pais gate error cooldown",
                context={"cooldown_s": cool, "pid": os.getpid()},
            )
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def seconds_until_pais_allowed(*, gate_dir: Path | None = None) -> float:
    """How long until the shared clock allows the next request. For tests and status."""
    _root, _lock, stamp_path = _paths(gate_dir)
    return max(0.0, _read_next_allowed(stamp_path) - time.time())
