"""Oxylabs dedicated-datacenter proxy. Password stays in the auth header, never in the URL."""

from __future__ import annotations

import os

import httpx

PAIS_ARCHIVE_URL = "https://www.pais.co.il/lotto/archive.aspx"
PAIS_CSV_URL = "https://www.pais.co.il/Lotto/lotto_resultsDownload.aspx"
PAIS_DRAW_URL = "https://www.pais.co.il/lotto/currentlotto.aspx?lotteryId={draw_number}"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


class PaisSourceError(RuntimeError):
    """The official site did not return usable data. Do not call Magayo for this."""


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


def open_pais_client() -> httpx.Client:
    """One client keeps the archive-page cookies for the CSV and draw pages."""
    user, password, proxy_url = _proxy_auth()
    return httpx.Client(
        proxy=httpx.Proxy(proxy_url, auth=(user, password)),
        timeout=45.0,
        follow_redirects=True,
        headers={"User-Agent": BROWSER_UA},
    )
