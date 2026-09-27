"""Append-only record of the eight lines sealed before a draw."""

from __future__ import annotations

import datetime
import hashlib
import json
from typing import Any

from logger import logger
from services.draw_prize import calculate_prize, draw_has_prize_data, draw_ticket_cost
from services.ticket_validator import count_hits
from services.git_sha import get_git_sha


def lines_hash(lines: list[dict[str, Any]]) -> str:
    canonical = [
        {"numbers": sorted(int(n) for n in line["numbers"]), "strong": int(line["strong"])}
        for line in lines
    ]
    raw = json.dumps(canonical, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record_shadow_commitment(
    db: Any,
    *,
    lines: list[dict[str, Any]],
    main_algorithm: str,
    strong_algorithm: str,
    training_cutoff: datetime.date,
    target_draw_number: int | None,
    ticket_pack_id: int | None,
) -> Any:
    """Add the row to the current transaction. The caller commits with the pack."""
    from models.validation_v2 import ShadowCommitment

    row = ShadowCommitment(
        lines=[{"numbers": list(line["numbers"]), "strong": int(line["strong"])} for line in lines],
        lines_hash=lines_hash(lines),
        generated_at=datetime.datetime.now(datetime.timezone.utc),
        git_sha=get_git_sha(),
        main_algorithm=main_algorithm,
        strong_algorithm=strong_algorithm,
        training_cutoff=training_cutoff,
        target_draw_number=target_draw_number,
        ticket_pack_id=ticket_pack_id,
    )
    db.add(row)
    db.flush()
    logger.info(
        "Shadow commitment sealed",
        context={"commitment_id": row.id, "target_draw_number": target_draw_number, "git_sha": row.git_sha},
    )
    return row


def settle_shadow_for_draw(db: Any, draw: Any) -> dict[str, Any]:
    """Write the outcome after the draw. Does not change the sealed lines."""
    from models.validation_v2 import ShadowCommitment, ShadowOutcome

    if getattr(draw, "draw_number", None) is None:
        return {"settled": 0, "reason": "draw_has_no_number"}
    commitments = (
        db.query(ShadowCommitment)
        .filter(ShadowCommitment.target_draw_number == int(draw.draw_number))
        .all()
    )
    settled = 0
    for commitment in commitments:
        existing = (
            db.query(ShadowOutcome).filter(ShadowOutcome.commitment_id == commitment.id).one_or_none()
        )
        wins = 0
        detail = []
        payout = 0.0
        cost = 0.0
        has_prize = draw_has_prize_data(draw)
        for line in commitment.lines:
            hits = count_hits(line["numbers"], draw.numbers)
            strong_hit = int(line["strong"]) == int(draw.strong_number)
            won = hits >= 3
            wins += int(won)
            line_prize = None
            if has_prize:
                line_prize = calculate_prize(draw, hits, strong_hit)
                if line_prize is not None:
                    payout += float(line_prize)
                    cost += draw_ticket_cost(draw)
            detail.append(
                {"numbers": line["numbers"], "strong": line["strong"], "hits": hits, "prize": line_prize}
            )
        if existing is None:
            db.add(
                ShadowOutcome(
                    commitment_id=commitment.id,
                    draw_id=draw.id,
                    settled_at=datetime.datetime.now(datetime.timezone.utc),
                    winning_lines=wins,
                    payout_ils=payout if has_prize else None,
                    cost_ils=cost if has_prize else None,
                    detail=detail,
                )
            )
            settled += 1
        elif existing.payout_ils is None and has_prize:
            existing.payout_ils = payout
            existing.cost_ils = cost
            existing.detail = detail
            existing.winning_lines = wins
            settled += 1
    if settled:
        db.commit()
    return {"settled": settled, "commitments": len(commitments)}
