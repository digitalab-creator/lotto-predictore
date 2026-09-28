"""Post-draw chain: settle real batches, walk-forward step, new pack, notify."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from logger import logger
from models import Draw, IngestState
from services.pack_notifier import PackNotifier
from services.prediction_service import PredictionService
from services.pais_draw_rules import CURRENT_REGIME_START
from services.real_ticket_settlement import RealTicketSettlementService
from services.shadow_commitment import settle_shadow_for_draw
from services.sync_draws import SyncDrawsResult, sync_draws_incremental
from services.ticket_pack_service import TicketPackService
from services.walk_forward_incremental import (
    append_walk_forward_for_latest_draw,
    ensure_walk_forward_bootstrapped,
)


class PostDrawChainService:
    def __init__(self, db: Session):
        self.db = db

    def run_after_sync(self, sync_result: SyncDrawsResult) -> dict[str, Any]:
        out: dict[str, Any] = {"sync": sync_result.to_dict(), "chain_ran": False}
        state = self.db.get(IngestState, 1)
        if state is not None and state.integrity_blocked:
            logger.error(
                "Arrr! Draw data is blocked — no new tickets until the CSV matches the database",
                context={"reason": state.integrity_reason},
            )
            out["skipped"] = "integrity_blocked"
            out["error"] = state.integrity_reason
            return out
        if sync_result.new_draws_added < 1:
            logger.info("Arrr! No new draw — post-draw chain skipped")
            out["skipped"] = "no_new_draw"
            return out

        out["chain_ran"] = True
        latest = (
            self.db.query(Draw)
            .filter(Draw.date >= CURRENT_REGIME_START)
            .order_by(Draw.date.desc())
            .first()
        )
        if not latest:
            out["error"] = "no_draw_in_db"
            return out

        settlement = RealTicketSettlementService(self.db).settle_submitted_pack_for_draw(latest)
        out["settlement"] = settlement
        out["shadow"] = settle_shadow_for_draw(self.db, latest)

        bootstrap = ensure_walk_forward_bootstrapped(self.db)
        out["walk_forward_bootstrap"] = bootstrap
        wf = append_walk_forward_for_latest_draw(self.db, include_dl=False)
        out["walk_forward_step"] = wf

        gen = PredictionService(self.db).generate_next_draw()
        out["generation"] = {
            "success": gen.get("success"),
            "pack_id": gen.get("ticket_pack_id"),
            "target_draw_number": gen.get("target_draw_number"),
        }
        if not gen.get("success"):
            out["error"] = gen.get("message")
            return out

        pack_id = gen.get("ticket_pack_id")
        if not pack_id:
            out["error"] = "missing_ticket_pack_id"
            return out
        pack = TicketPackService(self.db).get_pack(int(pack_id))
        if pack:
            from services.weekly_jobs_gate import (
                skipped_weekly_jobs_payload,
                weekly_email_and_jobs_enabled,
            )

            if weekly_email_and_jobs_enabled():
                notify = PackNotifier(self.db).send_pack(pack, last_draw=latest)
                out["notifications"] = notify
            else:
                out["notifications"] = skipped_weekly_jobs_payload(job="post_draw_pack_notify")
        return out

    def run_full(self, *, allow_magayo: bool = False) -> dict[str, Any]:
        sync_result = sync_draws_incremental(self.db, allow_magayo=allow_magayo)
        return self.run_after_sync(sync_result)
