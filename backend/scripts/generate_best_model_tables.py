import datetime
import os
import sys
import json
from pathlib import Path

# Add backend directory to Python path
backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from sqlalchemy import text
from db import SessionLocal
from logger import logger
from services.simulation_engine import SimulationEngine
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from models import Draw, Model
from config import NUM_COMBINATIONS_TO_RECOMMEND

def generate_best_model_tables():
    """
    Generates lottery tables using the best performing model combination (ROI > 1).
    Returns the generated tables and model info.
    """
    logger.info("Arrr! Starting best model table generation! Praisin' the FSM!")
    
    try:
        with SessionLocal() as db:
            # Find the best performing model combination with ROI > 1
            query = text("""
                SELECT
                    mm.name AS main_model_name,
                    sm.name AS strong_model_name,
                    COUNT(*) AS total_predictions,
                    ROUND(SUM(p.total_prize)::numeric, 2) AS total_prize,
                    ROUND(SUM(p.total_cost)::numeric, 2) AS total_cost,
                    ROUND(
                        CASE 
                            WHEN SUM(p.total_cost) = 0 THEN NULL
                            ELSE (SUM(p.total_prize)::numeric / NULLIF(SUM(p.total_cost), 0)::numeric)
                        END, 4
                    ) AS roi_ratio
                FROM
                    predictions p
                JOIN
                    models mm ON p.model_id = mm.id
                JOIN
                    models sm ON p.strong_model_id = sm.id
                GROUP BY
                    mm.name, sm.name
                HAVING
                    (SUM(p.total_prize)::numeric / NULLIF(SUM(p.total_cost), 0)::numeric) > 1
                ORDER BY
                    roi_ratio DESC
                LIMIT 1
            """)
            
            result = db.execute(query).fetchone()
            
            if not result:
                logger.warning("Arrr! No model combination found with ROI > 1!")
                return {
                    "success": False,
                    "message": "No model combination found with ROI > 1",
                    "tables": []
                }
            
            main_model_name = result.main_model_name
            strong_model_name = result.strong_model_name
            roi_ratio = result.roi_ratio
            total_prize = result.total_prize
            total_cost = result.total_cost
            
            logger.info(
                "Arrr! Found best performing model combination",
                context={
                    "main_model": main_model_name,
                    "strong_model": strong_model_name,
                    "roi_ratio": roi_ratio,
                    "total_prize": total_prize,
                    "total_cost": total_cost
                }
            )
            
            # Get all draws for the model to use
            draws = db.query(Draw).filter(Draw.strong_number <= 7).order_by(Draw.date.desc()).all()
            
            if len(draws) < 20:
                logger.error("Arrr! Not enough draws in database!")
                return {
                    "success": False,
                    "message": "Not enough draws in database",
                    "tables": []
                }
            
            # Get the model classes
            main_model_cls = ALGORITHM_REGISTRY.get(main_model_name)
            strong_model_cls = STRONG_NUMBER_REGISTRY.get(strong_model_name)
            
            if not main_model_cls or not strong_model_cls:
                logger.error(
                    "Arrr! Could not find model classes!",
                    context={
                        "main_model": main_model_name,
                        "strong_model": strong_model_name
                    }
                )
                return {
                    "success": False,
                    "message": f"Could not find model classes: {main_model_name}, {strong_model_name}",
                    "tables": []
                }
            
            # Use SimulationEngine to generate tables
            engine = SimulationEngine(db)
            
            # Use last 12 draws as test set, rest as training
            train_draws = draws[:-12]
            test_draws = draws[-12:]
            train_start = train_draws[0].date
            train_end = train_draws[-1].date
            test_count = 12
            
            # Set top_n according to algorithm requirements
            if main_model_name == 'top_6_overall_frequent_v2':
                top_n = 10
            else:
                top_n = 3
            
            # Run simulation with the best model
            results = engine.run_comparison(
                train_start=train_start,
                train_end=train_end,
                test_count=test_count,
                top_n=top_n,
                algo_names=[main_model_name],
                strong_algo_names=[strong_model_name],
                use_cache=True
            )
            
            # Get the best result
            best_result = results.get((main_model_name, strong_model_name))
            if not best_result:
                logger.error("Arrr! No results returned from simulation!")
                return {
                    "success": False,
                    "message": "No results returned from simulation",
                    "tables": []
                }
            
            # Get the combinations
            tables = []
            for combo in best_result.get('combos', []):
                table = {
                    "numbers": combo["numbers"],
                    "strong": combo.get("strong")
                }
                tables.append(table)
                
                if len(tables) >= NUM_COMBINATIONS_TO_RECOMMEND:
                    break
            
            # Store the result for email service
            result_data = {
                "success": True,
                "date": datetime.date.today().isoformat(),
                "tables": tables,
                "model_info": {
                    "main_model": main_model_name,
                    "strong_model": strong_model_name,
                    "roi_ratio": f"{roi_ratio:.2%}",
                    "total_prize": f"₪{total_prize:,.2f}",
                    "total_cost": f"₪{total_cost:,.2f}",
                    "total_predictions": result.total_predictions
                }
            }
            
            # Save to a temporary file for the email service
            temp_file = "/tmp/best_model_tables.json"
            with open(temp_file, 'w') as f:
                json.dump(result_data, f, indent=2)
            
            logger.info(
                "Arrr! Best model tables generated successfully!",
                context={
                    "num_tables": len(tables),
                    "main_model": main_model_name,
                    "strong_model": strong_model_name,
                    "roi_ratio": roi_ratio,
                    "temp_file": temp_file
                }
            )
            
            return result_data
            
    except Exception as e:
        logger.error(
            "Arrr! Best model table generation failed!",
            context={"error": str(e)}
        )
        raise

if __name__ == "__main__":
    generate_best_model_tables() 