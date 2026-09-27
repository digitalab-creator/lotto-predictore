"""Shared Pais gate — one clock, one lock, no private sleep timers."""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from services.pais_rate_limit import (
    mark_pais_error_cooldown,
    pais_request_slot,
    seconds_until_pais_allowed,
)


def _worker(gate: str, hits: object, interval: float) -> None:
    with pais_request_slot(gate_dir=Path(gate), min_interval=interval):
        hits.append(time.time())


def test_two_slots_are_serialized_on_shared_clock(tmp_path: Path):
    gate = tmp_path / "gate"
    interval = 0.25
    with multiprocessing.Manager() as manager:
        hits = manager.list()
        first = multiprocessing.Process(target=_worker, args=(str(gate), hits, interval))
        second = multiprocessing.Process(target=_worker, args=(str(gate), hits, interval))
        first.start()
        time.sleep(0.02)
        second.start()
        first.join(timeout=5)
        second.join(timeout=5)
        assert first.exitcode == 0
        assert second.exitcode == 0
        assert len(hits) == 2
        gap = abs(hits[1] - hits[0])
        assert gap >= interval - 0.05


def test_error_cooldown_extends_shared_clock(tmp_path: Path):
    gate = tmp_path / "gate"
    with pais_request_slot(gate_dir=gate, min_interval=0.05):
        pass
    mark_pais_error_cooldown(gate_dir=gate, cooldown=0.4)
    remaining = seconds_until_pais_allowed(gate_dir=gate)
    assert remaining >= 0.25
