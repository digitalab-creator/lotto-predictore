"""Guard weekly cron work and post-draw notifications."""

from __future__ import annotations

from typing import Any

from logger import logger
from shared.feature_flags import SKIPPED_WEEKLY_JOBS_MESSAGE, env_bool


def weekly_email_and_jobs_enabled() -> bool:
    return env_bool("WEEKLY_EMAIL_AND_JOBS_ENABLED", default=False)


def skipped_weekly_jobs_payload(*, job: str) -> dict[str, Any]:
    logger.info(
        "Arrr! Weekly job skipped — feature flag off",
        context={"job": job, "flag": "WEEKLY_EMAIL_AND_JOBS_ENABLED"},
    )
    return {
        "status": "skipped",
        "job": job,
        "message": SKIPPED_WEEKLY_JOBS_MESSAGE,
    }
