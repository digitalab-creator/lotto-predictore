from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db.base import SessionLocal
from datetime import date, datetime, timedelta
from services.simulation_engine import SimulationEngine
from models import Draw, Prediction, Model, GeneratedCombination
from config import NUM_COMBINATIONS_TO_RECOMMEND
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from logger import logger

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/generate-combinations", response_class=JSONResponse)
def generate_combinations(db: Session = Depends(get_db)):
    """
    Generate lottery combinations using the best performing algorithm based on recent simulations.
    This endpoint uses the same logic as the weekly combinations generation.
    """
    logger.info("Arrr! Starting combination generation, praisin' the FSM!")
    
    try:
        # Get all draws, filtering out strong_number == 8
        draws = db.query(Draw).filter(Draw.strong_number <= 7).order_by(Draw.date).all()
        filtered_count = db.query(Draw).filter(Draw.strong_number == 8).count()
        
        logger.info(
            "Arrr! Filtered out draws with strong_number == 8 for generation, praisin' the FSM!",
            context={"filtered_count": filtered_count, "total_after_filter": len(draws)}
        )
        
        if len(draws) < 20:
            logger.error("Not enough draws in database for recommendation.")
            return JSONResponse(content={"error": "Not enough draws in database for recommendation."}, status_code=400)
        
        # Use last 12 draws as test set, rest as training
        train_draws = draws[:-12]
        test_draws = draws[-12:]
        train_start = train_draws[0].date
        train_end = train_draws[-1].date
        test_count = 12
        
        # Find best algorithm pair by ROI using SimulationEngine
        engine = SimulationEngine(db)
        results = {}
        best_pair = None
        best_roi = float('-inf')
        
        for algo_name, algo_cls in ALGORITHM_REGISTRY.items():
            # Set top_n according to algorithm requirements
            if algo_name == 'top_6_overall_frequent_v2':
                top_n = 10
            else:
                top_n = 3
                
            logger.info(f"Running {algo_name} with top_n={top_n}")
            
            try:
                res = engine.run_comparison(train_start, train_end, test_count, top_n, algo_names=[algo_name])
                for (main_algo, strong_algo), r in res.items():
                    results[(main_algo, strong_algo)] = r
                    if r["roi"] > best_roi:
                        best_pair = (main_algo, strong_algo)
                        best_roi = r["roi"]
            except Exception as e:
                logger.error(
                    f"Skipping {algo_name} due to error: {e}",
                    context={"algo_name": algo_name, "error": str(e)}
                )
                continue
        
        if not best_pair:
            logger.error("No algorithm produced results.")
            return JSONResponse(content={"error": "No algorithm produced results."}, status_code=400)
        
        main_algo_name, strong_algo_name = best_pair
        main_algo_cls = ALGORITHM_REGISTRY[main_algo_name]
        strong_algo_cls = STRONG_NUMBER_REGISTRY[strong_algo_name]
        
        # Use correct top_n for the best algorithm
        if main_algo_name == 'top_6_overall_frequent_v2':
            top_n = 10
        else:
            top_n = 3
        
        # Generate combinations using all draws
        all_draws = draws
        combos = main_algo_cls().run(all_draws, top_n=top_n, num_to_recommend=NUM_COMBINATIONS_TO_RECOMMEND)
        strong_algo = strong_algo_cls()
        strong_number = strong_algo.predict(all_draws)
        
        now = datetime.utcnow()
        
        # Create a new Prediction row for this generation event
        new_prediction = Prediction(
            model_id=db.query(Model).filter(Model.name == main_algo_name).first().id,
            strong_model_id=db.query(Model).filter(Model.name == strong_algo_name).first().id,
            run_time=now,
            roi=best_roi,
            total_prize=results[best_pair]["total_prize"],
            total_cost=results[best_pair]["total_cost"],
            test_count=test_count,
            notes=f"Combination generation at {now.isoformat()} | Best ROI: {best_roi:.4f}",
            train_start_date=train_start,
            train_end_date=train_end,
            num_test_draws=test_count,
            main_model_params={"top_n": top_n, "num_to_recommend": NUM_COMBINATIONS_TO_RECOMMEND},
            strong_model_params={"strong_algo": strong_algo_name}
        )
        db.add(new_prediction)
        db.flush()  # Get the new prediction.id
        
        # Store each combo in DB
        stored_combos = []
        for idx, combo in enumerate(combos):
            generated = GeneratedCombination(
                prediction_id=new_prediction.id,
                numbers=combo["numbers"],
                strong_number=strong_number,
                position=idx+1,
                generated_at=now
            )
            db.add(generated)
            
            stored_combos.append({
                "numbers": combo["numbers"],
                "strong": strong_number,
                "position": idx+1
            })
            
            logger.info(
                f"Stored combo {idx+1}: {combo['numbers']} + {strong_number}",
                context={
                    "prediction_id": new_prediction.id,
                    "numbers": combo["numbers"],
                    "strong_number": strong_number,
                    "position": idx+1
                }
            )
        
        db.commit()
        
        logger.info(
            f"Arrr! Generated {len(combos)} combinations using {main_algo_name} + {strong_algo_name}",
            context={
                "main_algo": main_algo_name,
                "strong_algo": strong_algo_name,
                "best_roi": best_roi,
                "num_combinations": len(combos),
                "prediction_id": new_prediction.id
            }
        )
        
        return {
            "algorithm": main_algo_name,
            "strong_algorithm": strong_algo_name,
            "roi": best_roi,
            "total_prize": results[best_pair]["total_prize"],
            "total_cost": results[best_pair]["total_cost"],
            "num_test_draws": test_count,
            "combinations": stored_combos,
            "prediction_id": new_prediction.id,
            "train_start": train_start.isoformat(),
            "train_end": train_end.isoformat()
        }
        
    except Exception as e:
        logger.error(
            "Arrr! Error in combination generation!",
            context={"error": str(e)}
        )
        db.rollback()
        return JSONResponse(content={"error": f"Error generating combinations: {str(e)}"}, status_code=500) 