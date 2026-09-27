"""Prize amounts from the official draw page. The CSV does not include them."""

from __future__ import annotations

import re
from typing import Any

import httpx

from services.pais_proxy import PAIS_ARCHIVE_URL, PAIS_DRAW_URL, PaisSourceError

TIER_BY_LABEL = {
    "6 + חזק": "6_strong",
    "6": "6",
    "5 + חזק": "5_strong",
    "5": "5",
    "4 + חזק": "4_strong",
    "4": "4",
    "3 + חזק": "3_strong",
    "3": "3",
}
PRIZE_COLUMNS = {
    "6_strong": "prize_6_strong",
    "6": "prize_6",
    "5_strong": "prize_5_strong",
    "5": "prize_5",
    "4_strong": "prize_4_strong",
    "4": "prize_4",
    "3_strong": "prize_3_strong",
    "3": "prize_3",
}


def _money(text: str) -> float:
    return float(text.replace(",", ""))


def _tiers_from_list(html: str, list_id: str) -> dict[str, dict[str, float]]:
    match = re.search(rf'id="{list_id}"[\s\S]*?</ol>', html)
    if not match:
        raise PaisSourceError(f"Draw page missing prize list {list_id}")
    tiers: dict[str, dict[str, float]] = {}
    for item in re.findall(r"<li[\s\S]*?</li>", match.group(0)):
        label = re.search(r'רמת פרס ([^"]+)"', item)
        winners = re.search(r"מספר זוכים ([0-9,]+)", item)
        amount = re.search(r"סכום זכייה ([0-9,]+) ₪", item)
        if not (label and winners and amount):
            continue
        key = TIER_BY_LABEL.get(label.group(1).strip())
        if key is None:
            continue
        tiers[key] = {"winners": _money(winners.group(1)), "amount": _money(amount.group(1))}
    if "3" not in tiers:
        raise PaisSourceError(f"Draw page prize list {list_id} had no 3-match tier")
    return tiers


def parse_draw_detail_html(html: str) -> dict[str, Any]:
    regular = _tiers_from_list(html, "regularLottoList")
    double = _tiers_from_list(html, "doubleLottoList")
    first = re.search(
        r"סכום הפרס הראשון בהגרלה זו עמד על <strong>([0-9,]+) ₪</strong>\s*ובדאבל לוטו עד <strong>([0-9,]+)",
        html,
    )
    total = re.search(r"סך כל הפרסים שחולקו בהגרלה זו היה:\s*<strong>([0-9,]+)", html)
    parsed: dict[str, Any] = {
        "winners_per_tier": {"regular": regular, "double": double},
        "jackpot_lotto": _money(first.group(1)) if first else None,
        "jackpot_double": _money(first.group(2)) if first else None,
        "total_prizes": _money(total.group(1)) if total else None,
    }
    for key, column in PRIZE_COLUMNS.items():
        tier = regular.get(key)
        parsed[column] = tier["amount"] if tier else None
    return parsed


def is_pais_error_page(html: str) -> bool:
    """True when Pais returned the Hebrew server-error page."""
    return "שגיאה בשרת" in html


def fetch_draw_detail(client: httpx.Client, draw_number: int) -> dict[str, Any]:
    """One request. Spacing is the shared Pais gate — not a private sleep here."""
    url = PAIS_DRAW_URL.format(draw_number=draw_number)
    response = client.get(url, headers={"Referer": PAIS_ARCHIVE_URL})
    response.raise_for_status()
    if is_pais_error_page(response.text):
        raise PaisSourceError("Pais returned server error page")
    if "regularLottoList" not in response.text:
        raise PaisSourceError("Draw page missing prize list regularLottoList")
    return parse_draw_detail_html(response.text)
