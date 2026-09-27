"""Fill missing prize rows from the official Mifal HaPais draw page.

Bookkeeping and ROI verification only — does not change production strategy
(coverage wheel) or reopen the sealed holdout decision.

Uses the shared Pais gate only. On an error page: cool down, skip that draw,
keep going. Never invents a prize amount.
"""

from __future__ import annotations

from typing import Any

import httpx

from config import PAIS_MAX_FAILURES
from logger import logger
from models import Draw
from services.draw_prize import PAIS_CSV_SOURCE, PAIS_SOURCE, utc_now
from services.pais_draw_detail import fetch_draw_detail, is_pais_error_page
from services.pais_draw_rules import CURRENT_REGIME_START
from services.pais_proxy import PAIS_ARCHIVE_URL, PaisSourceError, open_pais_client
from services.pais_rate_limit import mark_pais_error_cooldown

_ARCHIVE_REFRESH_EVERY = 10


def pending_prize_draws(db: Any) -> list[Draw]:
    """Newest current-regime draws first, so a failure streak does not block 2025–2026."""
    return (
        db.query(Draw)
        .filter(
            Draw.date >= CURRENT_REGIME_START,
            Draw.prize_3.is_(None),
            Draw.draw_number.is_not(None),
        )
        .order_by(Draw.draw_number.desc())
        .all()
    )


def _warm_archive(client: httpx.Client) -> None:
    response = client.get(PAIS_ARCHIVE_URL)
    response.raise_for_status()
    if is_pais_error_page(response.text):
        raise PaisSourceError("Archive page returned Pais error page")


def backfill_missing_prizes(
    db: Any,
    *,
    max_failures: int = PAIS_MAX_FAILURES,
    max_draws: int | None = None,
) -> dict[str, int]:
    pending = pending_prize_draws(db)
    if max_draws is not None:
        pending = pending[:max_draws]
    filled = 0
    failures = 0
    consecutive_errors = 0
    stopped = False
    logger.info(
        "Pais prize backfill starting",
        context={"pending": len(pending), "since": CURRENT_REGIME_START.isoformat()},
    )
    if not pending:
        return {"pending": 0, "filled": 0, "failures": 0, "stopped_early": 0}

    with open_pais_client() as client:
        try:
            _warm_archive(client)
        except (httpx.HTTPError, PaisSourceError) as exc:
            mark_pais_error_cooldown()
            logger.error("Pais archive page failed before prize backfill", context={"error": str(exc)})
            return {"pending": len(pending), "filled": 0, "failures": 1, "stopped_early": 1}

        for draw in pending:
            try:
                prizes = fetch_draw_detail(client, int(draw.draw_number))
            except (httpx.HTTPError, PaisSourceError) as exc:
                failures += 1
                consecutive_errors += 1
                mark_pais_error_cooldown()
                logger.error(
                    "Pais prize page failed — skip draw, keep shared clock",
                    context={
                        "draw_number": draw.draw_number,
                        "error": str(exc),
                        "consecutive_errors": consecutive_errors,
                    },
                )
                try:
                    _warm_archive(client)
                except (httpx.HTTPError, PaisSourceError):
                    mark_pais_error_cooldown()
                if consecutive_errors >= max_failures:
                    stopped = True
                    logger.error("Pais prize backfill stopped after repeated error pages")
                    break
                continue

            consecutive_errors = 0
            for key, value in prizes.items():
                setattr(draw, key, value)
            if draw.source not in {PAIS_SOURCE, PAIS_CSV_SOURCE}:
                draw.source = PAIS_CSV_SOURCE
            draw.verified_at = utc_now()
            db.commit()
            filled += 1
            logger.info(
                "Pais prize row stored",
                context={"draw_number": draw.draw_number, "filled": filled},
            )
            if filled % _ARCHIVE_REFRESH_EVERY == 0:
                try:
                    _warm_archive(client)
                except (httpx.HTTPError, PaisSourceError) as exc:
                    mark_pais_error_cooldown()
                    logger.warning(
                        "Pais archive refresh failed during backfill",
                        context={"error": str(exc)},
                    )
    return {
        "pending": len(pending),
        "filled": filled,
        "failures": failures,
        "stopped_early": int(stopped),
    }
