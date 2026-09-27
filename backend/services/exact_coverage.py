"""Exact Lotto probabilities for the current 6/37 + strong 1–7 game.

One ticket's chance does not depend on which numbers you pick.
Eight tickets together do depend on overlap. That second number is counted
by walking every main-number combination, then weighting the strong number
by 1/7 and 6/7. That is the same result as listing all 16,273,488 draws.
"""

from __future__ import annotations

import math
from itertools import combinations
from typing import Any, Sequence

import numpy as np

from services.pais_draw_rules import REGULAR_MAX, STRONG_MAX

MAIN_SPACE = math.comb(REGULAR_MAX, 6)
TOTAL_OUTCOMES = MAIN_SPACE * STRONG_MAX
_BYTE_BITS = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)
_MASKS: np.ndarray | None = None

TIER_ORDER = (
    "6_strong",
    "6",
    "5_strong",
    "5",
    "4_strong",
    "4",
    "3_strong",
    "3",
)
TIER_HITS = {
    "6_strong": (6, True),
    "6": (6, False),
    "5_strong": (5, True),
    "5": (5, False),
    "4_strong": (4, True),
    "4": (4, False),
    "3_strong": (3, True),
    "3": (3, False),
}


def main_hit_ways(hits: int) -> int:
    """How many 6-number draws share exactly ``hits`` numbers with one ticket."""
    if hits < 0 or hits > 6:
        return 0
    return math.comb(6, hits) * math.comb(REGULAR_MAX - 6, 6 - hits)


def tier_probability(hits: int, strong_hit: bool) -> float:
    """Probability one ticket lands in this exact prize tier."""
    strong_weight = 1 / STRONG_MAX if strong_hit else (STRONG_MAX - 1) / STRONG_MAX
    return main_hit_ways(hits) / MAIN_SPACE * strong_weight


def any_prize_probability() -> float:
    """P(3 or more main numbers). Strong does not matter: both 3 and 3+strong pay."""
    ways = sum(main_hit_ways(k) for k in range(3, 7))
    return ways / MAIN_SPACE


ANY_PRIZE_PROBABILITY = any_prize_probability()


def one_in(probability: float) -> float | None:
    if probability <= 0:
        return None
    return 1.0 / probability


def independent_pack_any_prize(lines: int = 8) -> float:
    """P(at least one prize) if each line were an independent random ticket."""
    miss = 1.0 - ANY_PRIZE_PROBABILITY
    return 1.0 - miss**lines


def tier_name(hits: int, strong_hit: bool) -> str | None:
    if hits < 3:
        return None
    return f"{hits}_strong" if strong_hit else str(hits)


def _combo_masks() -> np.ndarray:
    """Bitmask of every 6-subset of 37 numbers. Built once per process."""
    global _MASKS
    if _MASKS is None:
        masks = np.empty(MAIN_SPACE, dtype=np.uint64)
        for index, combo in enumerate(combinations(range(REGULAR_MAX), 6)):
            mask = 0
            for bit in combo:
                mask |= 1 << bit
            masks[index] = mask
        _MASKS = masks
    return _MASKS


_CHUNK = 200_000


def _ticket_mask(numbers: Sequence[int]) -> int:
    mask = 0
    for number in numbers:
        mask |= 1 << (int(number) - 1)
    return mask


def _hits_for_ticket(ticket_mask: int) -> np.ndarray:
    """Hit counts for every main-number draw, in chunks so memory stays small."""
    masks = _combo_masks()
    out = np.empty(masks.shape[0], dtype=np.uint8)
    ticket = np.uint64(ticket_mask)
    for start in range(0, masks.shape[0], _CHUNK):
        chunk = masks[start : start + _CHUNK] & ticket
        byte_hits = _BYTE_BITS[chunk.view(np.uint8)].reshape(-1, 8).sum(axis=1, dtype=np.uint8)
        out[start : start + _CHUNK] = byte_hits
    return out


def _hit_matrix(lines: Sequence[dict[str, Any]]) -> np.ndarray:
    columns = [_hits_for_ticket(_ticket_mask(line["numbers"])) for line in lines]
    return np.stack(columns, axis=1)


def portfolio_p_any(lines: Sequence[dict[str, Any]]) -> float:
    """Exact P(at least one of these lines wins any prize)."""
    if not lines:
        return 0.0
    hits = _hit_matrix(lines)
    return float((hits >= 3).any(axis=1).mean())


def portfolio_p_main_at_least(lines: Sequence[dict[str, Any]], min_hits: int) -> float:
    """Exact P(at least one line has ``min_hits`` or more main numbers)."""
    if not lines or min_hits < 1:
        return 0.0
    hits = _hit_matrix(lines)
    return float((hits >= min_hits).any(axis=1).mean())


def portfolio_metrics(lines: Sequence[dict[str, Any]]) -> dict[str, float]:
    """Portfolio-level exact probabilities used by the wheel report and optimizer."""
    return {
        "p_any_prize": portfolio_p_any(lines),
        "p_4_plus": portfolio_p_main_at_least(lines, 4),
        "p_5_plus": portfolio_p_main_at_least(lines, 5),
        "p_6_plus": portfolio_p_main_at_least(lines, 6),
    }


def expected_winning_lines_per_draw(lines: Sequence[dict[str, Any]]) -> float:
    """Mean count of lines that win any prize on one random draw."""
    if not lines:
        return 0.0
    hits = _hit_matrix(lines)
    return float((hits >= 3).sum(axis=1).mean())


def exact_portfolio_report(lines: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Exact tier probabilities for this pack, plus the independent-8 baseline."""
    hits = _hit_matrix(lines)
    main_count = int(hits.shape[0])
    covered = (hits >= 3).any(axis=1)
    tier_counts = {name: 0 for name in TIER_ORDER}
    for strong in range(1, STRONG_MAX + 1):
        any_tier = {name: np.zeros(main_count, dtype=bool) for name in TIER_ORDER}
        for index, line in enumerate(lines):
            plus = int(line["strong"]) == strong
            column = hits[:, index]
            for k in range(3, 7):
                name = f"{k}_strong" if plus else str(k)
                any_tier[name] |= column == k
        for name, mask in any_tier.items():
            tier_counts[name] += int(mask.sum())

    outcome_count = main_count * STRONG_MAX
    tiers = {}
    for name in TIER_ORDER:
        probability = tier_counts[name] / outcome_count
        hits_k, strong_hit = TIER_HITS[name]
        single = tier_probability(hits_k, strong_hit)
        tiers[name] = {
            "probability": probability,
            "one_in": one_in(probability),
            "single_ticket_probability": single,
            "single_ticket_one_in": one_in(single),
            "independent_8_probability": 1.0 - (1.0 - single) ** len(lines),
        }
    p_any = float(covered.mean())
    metrics = portfolio_metrics(lines)
    return {
        "line_count": len(lines),
        "any_prize_main_outcomes": int(covered.sum()),
        "p_any_prize": p_any,
        "p_any_one_in": one_in(p_any),
        "independent_8_p_any": independent_pack_any_prize(len(lines)),
        "single_ticket_p_any": ANY_PRIZE_PROBABILITY,
        "expected_winning_lines_per_draw": expected_winning_lines_per_draw(lines),
        "expected_winning_lines_if_independent": len(lines) * ANY_PRIZE_PROBABILITY,
        "p_4_plus": metrics["p_4_plus"],
        "p_5_plus": metrics["p_5_plus"],
        "p_6_plus": metrics["p_6_plus"],
        "tiers": tiers,
    }


def theoretical_tier_table() -> list[dict[str, Any]]:
    """Published single-ticket odds, one row per prize, then any prize."""
    rows = []
    for name in TIER_ORDER:
        hits_k, strong_hit = TIER_HITS[name]
        probability = tier_probability(hits_k, strong_hit)
        rows.append(
            {
                "prize": name,
                "probability": probability,
                "one_in": one_in(probability),
            }
        )
    rows.append(
        {
            "prize": "any",
            "probability": ANY_PRIZE_PROBABILITY,
            "one_in": one_in(ANY_PRIZE_PROBABILITY),
        }
    )
    return rows
