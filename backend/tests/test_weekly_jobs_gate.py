"""Weekly outbound jobs feature flag."""

from __future__ import annotations

import pytest


def test_weekly_jobs_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEEKLY_EMAIL_AND_JOBS_ENABLED", raising=False)
    import importlib

    import shared.feature_flags as flags

    importlib.reload(flags)
    assert flags.WEEKLY_EMAIL_AND_JOBS_ENABLED is False


def test_weekly_jobs_enabled_when_env_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEEKLY_EMAIL_AND_JOBS_ENABLED", "true")
    import importlib

    import shared.feature_flags as flags

    importlib.reload(flags)
    assert flags.WEEKLY_EMAIL_AND_JOBS_ENABLED is True


def test_skipped_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEEKLY_EMAIL_AND_JOBS_ENABLED", "false")
    from services.weekly_jobs_gate import skipped_weekly_jobs_payload, weekly_email_and_jobs_enabled

    assert weekly_email_and_jobs_enabled() is False
    body = skipped_weekly_jobs_payload(job="test-job")
    assert body["status"] == "skipped"
    assert body["job"] == "test-job"
