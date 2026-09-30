"""Cron error email cooldown — avoids alert storms when jobs retry."""

from datetime import datetime, timedelta

import pytest


def test_error_email_skipped_within_cooldown(monkeypatch):
    monkeypatch.setenv("CRON_ERROR_EMAIL_COOLDOWN_SECONDS", "3600")
    from cron.error_handler import CronErrorHandler

    handler = CronErrorHandler()
    handler._last_error_email_at["post-draw-chain-daily"] = datetime.now()

    assert handler._should_send_error_email("post-draw-chain-daily") is False


def test_error_email_sent_after_cooldown(monkeypatch):
    monkeypatch.setenv("CRON_ERROR_EMAIL_COOLDOWN_SECONDS", "60")
    from cron.error_handler import CronErrorHandler

    handler = CronErrorHandler()
    handler._last_error_email_at["post-draw-chain-daily"] = datetime.now() - timedelta(seconds=120)

    assert handler._should_send_error_email("post-draw-chain-daily") is True
