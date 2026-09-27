"""Oxylabs dedicated-datacenter proxy. Password stays in the auth header, never in the URL.

Every request through ``open_pais_client`` waits on the shared Pais gate so sync,
prize backfill, and scripts never race each other with separate sleep timers.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from services.pais_rate_limit import pais_request_slot

PAIS_ARCHIVE_URL = "https://www.pais.co.il/lotto/archive.aspx"
PAIS_CSV_URL = "https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx"
PAIS_DRAW_URL = "https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId={draw_number}"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class PaisSourceError(RuntimeError):
    """The official site did not return usable data. Do not call Magayo for this."""


class PaisClient(httpx.Client):
    """httpx client that holds the shared Pais lock for every request."""

    def request(self, method: str, url: Any, **kwargs: Any) -> httpx.Response:
        with pais_request_slot():
            return super().request(method, url, **kwargs)


def _strip_env(raw: str | None) -> str:
    text = (raw or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        text = text[1:-1]
    if " #" in text:
        text = text.split(" #", 1)[0].rstrip()
    return text.strip()


def _proxy_auth() -> tuple[str, str, str]:
    user = _strip_env(os.getenv("OXYLABS_PROXY_USER"))
    password = _strip_env(os.getenv("OXYLABS_PROXY_PASS"))
    proxy_url = _strip_env(os.getenv("COURT_PROXY"))
    if user and not user.startswith(("user-", "customer-")):
        user = f"user-{user}"
    if not user or not password or not proxy_url:
        raise PaisSourceError(
            "Oxylabs is not configured (OXYLABS_PROXY_USER, OXYLABS_PROXY_PASS, COURT_PROXY)"
        )
    return user, password, proxy_url


def open_pais_client() -> PaisClient:
    """One client keeps archive cookies. Every GET waits on the shared Pais gate."""
    user, password, proxy_url = _proxy_auth()
    return PaisClient(
        proxy=httpx.Proxy(proxy_url, auth=(user, password)),
        timeout=45.0,
        follow_redirects=True,
        headers={"User-Agent": BROWSER_UA},
    )
