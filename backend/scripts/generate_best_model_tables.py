import json
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from db import SessionLocal
from logger import logger
from services.prediction_service import PredictionService


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
        "model_info": {
            "main_model": result["model_info"]["main_model"],
            "strong_model": result["model_info"]["strong_model"],
            "roi_ratio": "N/A (walk-forward scoreboard — Phase 4)",
            "total_prize": "₪0.00",
            "total_cost": f"₪{result['model_info']['planned_cost_ils']:.2f}",
            "total_predictions": 0,
            "strategy_source": result["model_info"]["strategy_source"],
            "training_cutoff": result["model_info"]["training_cutoff"],
            "target_draw_number": result["model_info"]["target_draw_number"],
        },
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
