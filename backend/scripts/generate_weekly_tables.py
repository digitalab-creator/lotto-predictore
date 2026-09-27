import datetime
import os
import sys
import requests
from pathlib import Path

# Add backend directory to Python path
backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from sqlalchemy import text
from db import SessionLocal, get_db
from models.weekly_winning_combination import WeeklyWinningCombination
from logger import logger
from services.simulation_engine import SimulationEngine
from algorithms.base import ALGORITHM_REGISTRY, STRONG_NUMBER_REGISTRY
from models import Draw, Model
from simulation_prize import calculate_prize
from simulation_print import print_weekly_tables

def generate_tables():
    """
    Generates lottery tables using the best performing model and parameters.
    Sends them via email.
    """
    logger.info("Arrr! Starting weekly table generation! Praisin' the FSM!")
    
    try:
        with SessionLocal() as db:
            # Get the best performing combination
            best_combo = db.query(WeeklyWinningCombination).order_by(
                WeeklyWinningCombination.total_roi.desc()
            ).first()
            
            if not best_combo:
                logger.error("Arrr! No winning combinations found in database!")
                return
            
            logger.info(
                "Arrr! Found best performing combination",
                context={
                    "model_id": best_combo.model_id,
                    "strong_model_id": best_combo.strong_model_id,
                    "total_roi": best_combo.total_roi
                }
            )
            
            # Get all draws for the model to use
            from services.pais_draw_rules import CURRENT_REGIME_START

            draws = db.query(Draw).filter(Draw.date >= CURRENT_REGIME_START).order_by(Draw.date.desc()).all()
            
            # Parse model parameters
            main_params = json.loads(best_combo.main_model_params)
            strong_params = json.loads(best_combo.strong_model_params)
            
            # Get training parameters
            training_params = main_params.get('training_params', {})
            train_start = datetime.datetime.fromisoformat(training_params.get('train_start_date')).date() if training_params.get('train_start_date') else draws[-12].date
            train_end = datetime.datetime.fromisoformat(training_params.get('train_end_date')).date() if training_params.get('train_end_date') else draws[-1].date
            test_count = training_params.get('test_count', 1)
            
            logger.info(
                "Arrr! Using training parameters",
                context={
                    "train_start": train_start.isoformat(),
                    "train_end": train_end.isoformat(),
                    "test_count": test_count
                }
            )
            
            # Get the model classes
            main_model_name = main_params.get('model_version', 'sequence_lstm_classifier')
            strong_model_name = strong_params.get('strong_algo', 'random')
            
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
                return
            
            # Use SimulationEngine to generate tables
            engine = SimulationEngine(db)
            
            # Run simulation with the best model
            results = engine.run_comparison(
                train_start=train_start,
                train_end=train_end,
                test_count=test_count,
                top_n=main_params.get('top_n', 3),
                algo_names=[main_model_name],
                strong_algo_names=[strong_model_name],
                use_cache=True
            )
            
            # Get the best result
            best_result = results.get((main_model_name, strong_model_name))
            if not best_result:
                logger.error("Arrr! No results returned from simulation!")
                return
            
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
            
            # Send email
            send_tables_email(tables, best_combo)
            
            logger.info("Arrr! Weekly table generation completed successfully!")
            
    except Exception as e:
        logger.error(
            "Arrr! Weekly table generation failed!",
            context={"error": str(e)}
        )
        raise

def send_tables_email(tables, best_combo):
    """
    Sends an email with the generated tables using the email microservice.
    """
    try:
        # Prepare data for email service
        email_data = {
            "date": datetime.date.today().isoformat(),
            "tables": [
                {
                    "numbers": table['numbers'],
                    "strong": table['strong']
                }
                for table in tables
            ],
            "model_info": {
                "model_id": best_combo.model_id,
                "strong_model_id": best_combo.strong_model_id,
                "total_roi": f"{best_combo.total_roi:.2%}",
                "num_tickets": best_combo.num_tickets,
                "total_prize": f"₪{best_combo.total_prize:,.2f}"
            }
        }
        
        email_url = os.getenv("EMAIL_SERVICE_URL", "http://email-service:8000").rstrip("/")
        # Send request to email service
        response = requests.post(
            f"{email_url}/send-weekly-tables",
            json=email_data,
            timeout=30,
        )
        
        if response.status_code != 200:
            raise Exception(f"Email service returned status code {response.status_code}: {response.text}")
            
        logger.info("Arrr! Email sent successfully!")
        
    except Exception as e:
        logger.error(
            "Arrr! Failed to send email!",
            context={"error": str(e)}
        )
        raise

if __name__ == "__main__":
    generate_tables() 