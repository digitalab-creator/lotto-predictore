#!/usr/bin/env python3
"""
Lotto stack limits from host load — always low CPU priority vs other apps.

- cpu_shares stay far below Docker default (1024) so n8n/WP/etc. win when they need CPU.
- oom_score_adj is high so lotto is reclaimed before other workloads under RAM pressure.
- When the host is clear, CPU/RAM ceilings rise toward spare capacity (not fixed tiny caps).
- If non-lotto containers are actively using CPU, lotto tier is capped immediately.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

TIER_ORDER = ("busy", "balanced", "idle")
TIER_RANK = {name: idx for idx, name in enumerate(TIER_ORDER)}
STATE_PATH = Path(__file__).resolve().parent.parent / "tmp" / "resource_governor_state.json"
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "resource_governor.yaml"


def _load_config(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML required: pip install pyyaml (or use system python3-yaml)")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("config must be a mapping")
    return data


def _meminfo_kb() -> tuple[int, int]:
    meminfo: dict[str, int] = {}
    with open("/proc/meminfo", encoding="utf-8") as f:
        for line in f:
            if ":" not in line:
                continue
            key, rest = line.split(":", 1)
            meminfo[key] = int(rest.strip().split()[0])
    total_kb = meminfo.get("MemTotal", 0)
    avail_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    return total_kb, avail_kb


def _read_mem_pressure() -> float:
    total_kb, avail_kb = _meminfo_kb()
    if total_kb <= 0:
        return 0.5
    return 1.0 - (avail_kb / total_kb)


def _read_cpu_pressure(sample_seconds: float = 0.5) -> float:
    def snapshot() -> tuple[int, int]:
        with open("/proc/stat", encoding="utf-8") as f:
            parts = f.readline().split()
        if len(parts) < 5:
            return 0, 1
        user, nice, system, idle = (int(parts[i]) for i in range(1, 5))
        iowait = int(parts[5]) if len(parts) > 5 else 0
        idle_all = idle + iowait
        total = user + nice + system + idle_all
        for i in range(6, min(len(parts), 8)):
            total += int(parts[i])
        return idle_all, total

    idle0, total0 = snapshot()
    time.sleep(sample_seconds)
    idle1, total1 = snapshot()
    dt = total1 - total0
    if dt <= 0:
        return 0.5
    usage = 1.0 - ((idle1 - idle0) / dt)
    return max(0.0, min(1.0, usage))


def _host_pressure() -> tuple[float, float, float]:
    cpu_p = _read_cpu_pressure()
    mem_p = _read_mem_pressure()
    return max(cpu_p, mem_p), cpu_p, mem_p


def _parse_cpu_percent(raw: str) -> float:
    raw = (raw or "").strip().rstrip("%")
    if not raw or raw == "--":
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _non_lotto_container_cpu(project_name: str) -> tuple[float, float]:
    """Return (sum_cpu%, max_single_cpu%) for running containers outside this compose project."""
    result = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.CPUPerc}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    total = 0.0
    peak = 0.0
    needle = project_name.lower()
    for line in (result.stdout or "").splitlines():
        if "\t" not in line:
            continue
        name, cpu_raw = line.split("\t", 1)
        if needle in name.lower():
            continue
        pct = _parse_cpu_percent(cpu_raw)
        total += pct
        peak = max(peak, pct)
    return total, peak


def _cap_tier_for_competition(proposed: str, other_cpu_sum: float, cfg: dict[str, Any]) -> str:
    yield_cfg = cfg.get("yield_to_others", {})
    busy_at = float(yield_cfg.get("other_containers_cpu_busy_pct", 10.0))
    balanced_at = float(yield_cfg.get("other_containers_cpu_balanced_pct", 4.0))
    if other_cpu_sum >= busy_at:
        return "busy"
    if other_cpu_sum >= balanced_at and TIER_RANK[proposed] > TIER_RANK["balanced"]:
        return "balanced"
    return proposed


def _propose_tier(pressure: float, cfg: dict[str, Any]) -> str:
    thresholds = cfg.get("pressure", {})
    idle_below = float(thresholds.get("idle_below", 0.38))
    busy_above = float(thresholds.get("busy_above", 0.68))
    if pressure <= idle_below:
        return "idle"
    if pressure >= busy_above:
        return "busy"
    return "balanced"


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"tier": "busy", "idle_streak": 0}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"tier": "busy", "idle_streak": 0}


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _resolve_tier(
    proposed: str, previous: str, idle_streak: int, cfg: dict[str, Any]
) -> tuple[str, int]:
    hysteresis = cfg.get("hysteresis", {})
    need_idle = int(hysteresis.get("idle_samples_to_scale_up", 3))
    if TIER_RANK[proposed] <= TIER_RANK[previous]:
        return proposed, 0
    if proposed == "balanced":
        return "balanced", 0
    idle_streak += 1
    if idle_streak >= need_idle:
        return "idle", 0
    if TIER_RANK[previous] < TIER_RANK["balanced"]:
        return "balanced", idle_streak
    return previous, idle_streak


def _parse_memory_mb(value: str) -> float:
    m = re.match(r"^(\d+(?:\.\d+)?)([mMgG])?$", str(value).strip())
    if not m:
        return 512.0
    amount = float(m.group(1))
    unit = (m.group(2) or "m").lower()
    return amount * (1024.0 if unit == "g" else 1.0)


def _format_memory(mb: float) -> str:
    mb = max(64.0, mb)
    if mb >= 1024.0 and abs(mb - round(mb / 1024.0) * 1024.0) < 1.0:
        return f"{int(round(mb / 1024.0))}g"
    return f"{int(round(mb))}m"


def _format_cpus(value: float) -> str:
    value = max(0.08, value)
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _static_limits(service_cfg: dict[str, Any], tier: str) -> dict[str, Any]:
    key = tier if tier != "idle" else "idle_min"
    if key not in service_cfg and tier in service_cfg:
        key = tier
    base = dict(service_cfg[key])
    return base


def _dynamic_idle_budget(cfg: dict[str, Any], ncpus: int) -> tuple[float, float]:
    dyn = cfg.get("dynamic_idle", {})
    _, avail_kb = _meminfo_kb()
    avail_mb = avail_kb / 1024.0
    reserve_cpus = float(dyn.get("reserve_cpus", 1.25))
    reserve_mb = float(dyn.get("reserve_memory_mb", 2400))
    cpu_frac = float(dyn.get("spare_cpu_fraction", 0.72))
    mem_frac = float(dyn.get("spare_memory_fraction", 0.55))
    spare_cpus = max(0.0, ncpus - reserve_cpus)
    spare_mb = max(0.0, avail_mb - reserve_mb)
    return spare_cpus * cpu_frac, spare_mb * mem_frac


def _effective_limits(
    service: str,
    service_cfg: dict[str, Any],
    tier: str,
    cfg: dict[str, Any],
    ncpus: int,
) -> dict[str, Any]:
    limits = _static_limits(service_cfg, tier)
    yield_cfg = cfg.get("yield_to_others", {})
    shares_map = yield_cfg.get("cpu_shares", {})
    limits["cpu_shares"] = int(shares_map.get(tier, shares_map.get("busy", 64)))

    dyn = cfg.get("dynamic_idle", {})
    if tier != "idle" or not dyn.get("enabled", True):
        return limits

    weights: dict[str, float] = dyn.get("service_weights", {})
    weight = float(weights.get(service, 0.0))
    if weight <= 0:
        return limits

    cpu_budget, mem_budget_mb = _dynamic_idle_budget(cfg, ncpus)
    min_limits = service_cfg.get("idle_min", limits)
    dyn_cpus = max(float(min_limits.get("cpus", limits["cpus"])), cpu_budget * weight)
    dyn_mem = max(
        _parse_memory_mb(str(min_limits.get("memory", limits["memory"]))),
        mem_budget_mb * weight,
    )
    limits["cpus"] = _format_cpus(dyn_cpus)
    limits["memory"] = _format_memory(dyn_mem)
    return limits


def _compose_container_id(compose_dir: Path, service: str) -> str | None:
    result = subprocess.run(
        ["docker", "compose", "ps", "-q", service],
        cwd=compose_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    cid = (result.stdout or "").strip().splitlines()
    if not cid:
        return None
    return cid[0].strip()


def _docker_update(container_id: str, limits: dict[str, Any], dry_run: bool) -> list[str]:
    cmd = [
        "docker",
        "update",
        f"--cpus={limits['cpus']}",
        f"--memory={limits['memory']}",
        f"--memory-swap={limits['memory']}",
        f"--cpu-shares={int(limits['cpu_shares'])}",
        f"--pids-limit={int(limits['pids'])}",
        container_id,
    ]
    if dry_run:
        return [" ".join(cmd)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return []


def _limits_signature(limits: dict[str, Any]) -> str:
    return json.dumps(
        {
            k: limits[k]
            for k in ("cpus", "memory", "cpu_shares", "pids")
            if k in limits
        },
        sort_keys=True,
    )


def run(config_path: Path, dry_run: bool) -> int:
    cfg = _load_config(config_path)
    compose_dir = Path(cfg.get("compose_project_dir", DEFAULT_CONFIG.parent.parent))
    project_name = str(cfg.get("compose_project_name", "lotto-predictore"))
    if not compose_dir.is_dir():
        print(f"compose_project_dir missing: {compose_dir}", file=sys.stderr)
        return 1

    ncpus = os.cpu_count() or 2
    pressure, cpu_p, mem_p = _host_pressure()
    other_cpu_sum, other_cpu_peak = _non_lotto_container_cpu(project_name)
    proposed = _cap_tier_for_competition(_propose_tier(pressure, cfg), other_cpu_sum, cfg)

    state = _load_state()
    previous = str(state.get("tier", "busy"))
    idle_streak = int(state.get("idle_streak", 0))
    tier, idle_streak = _resolve_tier(proposed, previous, idle_streak, cfg)

    services_cfg = cfg.get("services", {})
    applied: list[str] = []
    skipped: list[str] = []
    prev_sigs = state.get("limits_signatures", {})
    new_sigs: dict[str, str] = {}

    for service, service_cfg in services_cfg.items():
        tier_key = tier
        if tier == "idle" and "idle_min" not in service_cfg and tier not in service_cfg:
            skipped.append(f"{service}: no idle profile")
            continue
        if tier != "idle" and tier not in service_cfg:
            skipped.append(f"{service}: no {tier} tier")
            continue

        limits = _effective_limits(service, service_cfg, tier_key, cfg, ncpus)
        sig = _limits_signature(limits)
        new_sigs[service] = sig

        cid = _compose_container_id(compose_dir, service)
        if not cid:
            skipped.append(f"{service}: not running")
            continue

        if not dry_run and sig == prev_sigs.get(service) and tier == previous:
            applied.append(f"{service}: unchanged ({tier})")
            continue

        try:
            cmds = _docker_update(cid, limits, dry_run=dry_run)
            applied.extend(
                cmds
                if dry_run
                else [
                    f"{service} -> {tier} cpus={limits['cpus']} mem={limits['memory']} "
                    f"shares={limits['cpu_shares']}"
                ]
            )
        except subprocess.CalledProcessError as exc:
            print(f"docker update failed for {service}: {exc.stderr}", file=sys.stderr)
            return 1

    if not dry_run:
        _save_state(
            {
                "tier": tier,
                "idle_streak": idle_streak,
                "pressure": round(pressure, 3),
                "other_containers_cpu_sum": round(other_cpu_sum, 2),
                "limits_signatures": new_sigs,
            }
        )

    cpu_budget, mem_budget = _dynamic_idle_budget(cfg, ncpus) if tier == "idle" else (None, None)
    print(
        json.dumps(
            {
                "host_pressure": round(pressure, 3),
                "cpu_pressure": round(cpu_p, 3),
                "mem_pressure": round(mem_p, 3),
                "other_containers_cpu_sum_pct": round(other_cpu_sum, 2),
                "other_containers_cpu_peak_pct": round(other_cpu_peak, 2),
                "proposed_tier": proposed,
                "applied_tier": tier,
                "previous_tier": previous,
                "idle_streak": idle_streak,
                "idle_spare_cpu_budget": round(cpu_budget, 2) if cpu_budget is not None else None,
                "idle_spare_mem_budget_mb": round(mem_budget, 0) if mem_budget is not None else None,
                "lotto_cpu_shares_note": "128 idle max vs 1024 default; oom_score_adj=750 set in compose",
                "applied": applied,
                "skipped": skipped,
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Dynamic CPU/RAM limits for lotto containers")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return run(args.config, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
