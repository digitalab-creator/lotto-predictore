import json
import os
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from db import SessionLocal
from logger import logger
from services.prediction_service import PredictionService


def _pack_public_url(pack_id: int | None) -> str | None:
    if pack_id is None:
        return None
    base = os.getenv("PUBLIC_BASE_URL", os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000"))
    return f"{base.rstrip('/')}/ticket-packs/{pack_id}"


def _email_model_info(result: dict) -> dict:
    """Map production pack metadata to email fields (no legacy predictions ROI)."""
    mi = result.get("model_info") or {}
    lines = result.get("tables") or []
    percentile = mi.get("random_percentile")
    n_draws = mi.get("independent_draw_count")
    edge_bits: list[str] = []
    if mi.get("no_edge") or mi.get("detail") == "NO EVIDENCE OF PREDICTIVE EDGE":
        edge_bits.append("NO EVIDENCE OF PREDICTIVE EDGE")
    elif percentile is not None and n_draws is not None:
        edge_bits.append(f"Simulated vs random: {float(percentile):.1f}th percentile (n={int(n_draws)})")
    elif mi.get("source") == "config":
        edge_bits.append(f"Strategy from config ({mi.get('detail', 'fallback')})")
    else:
        edge_bits.append("Walk-forward scoreboard not loaded — strategy from config")

    return {
        "main_model": mi.get("main_model"),
        "strong_model": mi.get("strong_model"),
        "strategy_source": mi.get("strategy_source"),
        "training_cutoff": mi.get("training_cutoff"),
        "target_draw_number": mi.get("target_draw_number"),
        "planned_cost_ils": mi.get("planned_cost_ils"),
        "lines_count": len(lines),
        "edge_summary": " · ".join(edge_bits),
        "ticket_pack_id": result.get("ticket_pack_id"),
        "pack_url": _pack_public_url(result.get("ticket_pack_id")),
        # Legacy template keys — kept so old mailer does not show fake zeros
        "roi_ratio": edge_bits[0] if edge_bits else "See walk-forward scoreboard",
        "total_prize": "N/A (not a historical backtest — see walk-forward tables)",
        "total_cost": f"₪{float(mi.get('planned_cost_ils', 24)):.2f}",
        "total_predictions": len(lines),
    }


def generate_best_model_tables():
    """
    Build the next-draw ticket pack via PredictionService.generate_next_draw().
    Legacy name kept for cron/email wiring; no backtest dates or SUM(predictions) ranking.
    """
    logger.info("Arrr! Starting production ticket pack generation! Praisin' the FSM!")

    with SessionLocal() as db:
        service = PredictionService(db)
        result = service.generate_next_draw()

    if not result.get("success"):
        logger.warning(
            "Arrr! Production ticket pack generation failed",
            context={"message": result.get("message")},
        )
        return result

    temp_file = "/tmp/best_model_tables.json"
    email_payload = {
        "success": True,
        "date": result["date"],
        "tables": result["tables"],
        "model_info": _email_model_info(result),
        "ticket_pack_id": result.get("ticket_pack_id"),
        "pack_url": _pack_public_url(result.get("ticket_pack_id")),
    }
    with open(temp_file, "w", encoding="utf-8") as handle:
        json.dump(email_payload, handle, indent=2)

    logger.info(
        "Arrr! Production ticket pack saved for email",
        context={
            "temp_file": temp_file,
            "prediction_id": result.get("prediction_id"),
            "num_tables": len(result["tables"]),
        },
    )
    return email_payload


if __name__ == "__main__":
    generate_best_model_tables()
