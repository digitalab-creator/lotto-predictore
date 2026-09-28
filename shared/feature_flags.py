"""Runtime feature flags — env only, default off unless noted."""

from __future__ import annotations

import os


def env_bool(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


# Weekly table/combination jobs and outbound pack email/WhatsApp after a draw.
WEEKLY_EMAIL_AND_JOBS_ENABLED = env_bool("WEEKLY_EMAIL_AND_JOBS_ENABLED", default=False)

SKIPPED_WEEKLY_JOBS_MESSAGE = (
    "WEEKLY_EMAIL_AND_JOBS_ENABLED is false — weekly jobs and pack notifications are off."
)
