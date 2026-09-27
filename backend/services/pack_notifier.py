"""Email + WhatsApp delivery for ticket packs."""

from __future__ import annotations

import datetime
import os
from typing import Any

import httpx

from logger import logger
from models import Draw
from models.ticket_pack import PackDelivery, TicketPack
from services.real_ticket_settlement import RealTicketSettlementService
from services.ticket_pack_service import TicketPackService, pack_lines_copy_block
from services.whatsapp_service import send_whatsapp_text, whatsapp_configured
from sqlalchemy.orm import Session


def _public_pack_url(pack_id: int) -> str:
    base = os.getenv("PUBLIC_BASE_URL", os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000"))
    return f"{base.rstrip('/')}/ticket-packs/{pack_id}"


def build_pack_message(
    db: Session,
    pack: TicketPack,
    *,
    last_draw: Draw | None = None,
) -> dict[str, Any]:
    svc = TicketPackService(db)
    payload = svc.pack_public_payload(pack)
    meta = pack.strategy_meta or {}
    percentile = meta.get("random_percentile")
    n_draws = meta.get("independent_draw_count")
    edge_line = ""
    if pack.no_edge_label:
        edge_line = pack.no_edge_label
    elif percentile is not None:
        edge_line = f"Simulated vs random: {percentile:.1f}th percentile (n={n_draws})"

    real = RealTicketSettlementService(db).latest_settled_real_summary()
    real_line = "Real P&L (submitted packs only): no settled batches yet."
    if real:
        real_line = (
            f"Real P&L (last submitted batch): investment ₪{real['investment_ils']:.0f}, "
            f"payout ₪{real['payout_ils']:.0f}, net ₪{real['net_ils']:.0f}"
        )

    last_result = ""
    if last_draw:
        nums = " ".join(f"{int(n):02d}" for n in last_draw.numbers)
        last_result = (
            f"Last result (draw {last_draw.draw_number}): {nums} | חזק {last_draw.strong_number}"
        )

    date_str = pack.target_draw_date.isoformat() if pack.target_draw_date else "TBD"
    draw_num = pack.target_draw_number or "?"
    subject = f"Lotto {draw_num} — 8 tickets for {date_str}"
    body_text = "\n".join(
        [
            subject,
            "",
            last_result,
            edge_line,
            real_line,
            "",
            "Copy-ready lines (₪24 planned):",
            pack_lines_copy_block(pack.lines),
            "",
            f"Open pack: {_public_pack_url(pack.id)}",
            "",
            "Walk to a physical Mifal HaPais counter — software stops before the cash register.",
        ]
    )
    return {
        "subject": subject,
        "body_text": body_text,
        "pack_url": _public_pack_url(pack.id),
        "email_payload": {
            "subject": subject,
            "template_name": "ticket_pack.html",
            "template_data": {
                "subject": subject,
                "pack": payload,
                "last_draw": {
                    "draw_number": last_draw.draw_number if last_draw else None,
                    "numbers": list(last_draw.numbers) if last_draw else [],
                    "strong_number": last_draw.strong_number if last_draw else None,
                    "date": last_draw.date.isoformat() if last_draw else None,
                },
                "edge_line": edge_line,
                "real_line": real_line,
                "pack_url": _public_pack_url(pack.id),
            },
        },
    }


class PackNotifier:
    def __init__(self, db: Session):
        self.db = db
        self.email_url = os.getenv("EMAIL_SERVICE_URL", "http://email-service:8000")

    def send_pack(self, pack: TicketPack, *, last_draw: Draw | None = None) -> dict[str, Any]:
        message = build_pack_message(self.db, pack, last_draw=last_draw)
        results: dict[str, Any] = {"email": None, "whatsapp": None}
        now = datetime.datetime.now(datetime.timezone.utc)

        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    f"{self.email_url}/send-email",
                    json=message["email_payload"],
                )
            email_ok = resp.status_code < 400
            detail = resp.text[:500] if not email_ok else "sent"
        except httpx.HTTPError as exc:
            email_ok = False
            detail = str(exc)
            logger.error("Arrr! Pack email failed", context={"error": detail})

        self.db.add(
            PackDelivery(
                ticket_pack_id=pack.id,
                channel="email",
                success=email_ok,
                detail=detail,
                sent_at=now,
            )
        )
        results["email"] = {"success": email_ok, "detail": detail}

        wa = send_whatsapp_text(f"{message['subject']}\n\n{message['body_text']}")
        self.db.add(
            PackDelivery(
                ticket_pack_id=pack.id,
                channel="whatsapp",
                success=bool(wa.get("success")),
                detail=str(wa.get("detail"))[:2000],
                sent_at=now,
            )
        )
        if not wa.get("configured"):
            logger.info("Arrr! WhatsApp skipped — not configured")
        results["whatsapp"] = wa
        self.db.commit()
        return results
