import datetime
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from db import SessionLocal
from models.weekly_winning_combination import WeeklyWinningCombination
from services.logger import dh_log
import traceback
import json

def update_weekly_winning_combinations():
    """
    Updates the top 5 winning model combinations for the current week.
    This should be run once per week.
    """
    start_time = datetime.datetime.utcnow()
    dh_log(
        "Arrr! Starting weekly winning combinations update! Praisin' the FSM!",
        level="INFO",
        context={"start_time": start_time.isoformat()}
    )
    
    try:
        # Calculate week start and end dates
        today = datetime.date.today()
        week_start = today - datetime.timedelta(days=today.weekday())
        week_end = week_start + datetime.timedelta(days=6)
        
        dh_log(
            "Arrr! Processing week range",
            level="INFO",
            context={"week_start": week_start.isoformat(), "week_end": week_end.isoformat()}
        )
        
        with SessionLocal() as db:
            # Delete existing combinations for this week
            deleted = db.query(WeeklyWinningCombination).filter(
                WeeklyWinningCombination.week_start_date == week_start,
                WeeklyWinningCombination.week_end_date == week_end
            ).delete()
            
            dh_log(
                f"Arrr! Deleted {deleted} existing combinations for this week",
                level="INFO",
                context={"deleted_count": deleted}
            )
            
            # First check if we have any data in the date range
            check_query = text("""
                SELECT COUNT(*) as count
                FROM prediction_details d
                WHERE d.test_draw_date BETWEEN :week_start AND :week_end
            """)
            
            count_result = db.execute(check_query, {"week_start": week_start, "week_end": week_end}).scalar()
            
            if count_result == 0:
                dh_log(
                    "Arrr! No prediction details found for this week, using all-time data instead!",
                    level="WARNING",
                    context={"week_start": week_start.isoformat(), "week_end": week_end.isoformat()}
                )
                # Use all-time data if no data for this week
                query = text("""
                    SELECT
                        p.model_id,
                        p.strong_model_id,
                        p.main_model_params::text AS main_model_params,
                        p.strong_model_params::text AS strong_model_params,
                        ROUND(SUM(d.prize)::numeric / NULLIF(COUNT(d.id) * 3.10, 0)::numeric - 1, 4) AS total_roi,
                        COUNT(DISTINCT p.id) AS num_prediction_runs,
                        COUNT(d.id) AS num_tickets,
                        ROUND((COUNT(d.id) * 3.10)::numeric, 2) AS total_cost,
                        ROUND(SUM(d.prize)::numeric, 2) AS total_prize,
                        MIN(p.train_start_date) AS train_start_date,
                        MAX(p.train_end_date) AS train_end_date,
                        MAX(p.num_test_draws) AS test_count
                    FROM
                        prediction_details d
                    JOIN
                        predictions p ON p.id = d.prediction_id
                    GROUP BY
                        p.model_id, p.strong_model_id, p.main_model_params::text, p.strong_model_params::text
                    ORDER BY
                        total_roi DESC
                    LIMIT 5
                """)
                results = db.execute(query).fetchall()
            else:
                dh_log(
                    f"Arrr! Found {count_result} prediction details for this week!",
                    level="INFO",
                    context={"week_start": week_start.isoformat(), "week_end": week_end.isoformat()}
                )
                # Use weekly data
                query = text("""
                    SELECT
                        p.model_id,
                        p.strong_model_id,
                        p.main_model_params::text AS main_model_params,
                        p.strong_model_params::text AS strong_model_params,
                        ROUND(SUM(d.prize)::numeric / NULLIF(COUNT(d.id) * 3.10, 0)::numeric - 1, 4) AS total_roi,
                        COUNT(DISTINCT p.id) AS num_prediction_runs,
                        COUNT(d.id) AS num_tickets,
                        ROUND((COUNT(d.id) * 3.10)::numeric, 2) AS total_cost,
                        ROUND(SUM(d.prize)::numeric, 2) AS total_prize,
                        MIN(p.train_start_date) AS train_start_date,
                        MAX(p.train_end_date) AS train_end_date,
                        MAX(p.num_test_draws) AS test_count
                    FROM
                        prediction_details d
                    JOIN
                        predictions p ON p.id = d.prediction_id
                    WHERE
                        d.test_draw_date BETWEEN :week_start AND :week_end
                    GROUP BY
                        p.model_id, p.strong_model_id, p.main_model_params::text, p.strong_model_params::text
                    ORDER BY
                        total_roi DESC
                    LIMIT 5
                """)
                results = db.execute(query, {"week_start": week_start, "week_end": week_end}).fetchall()
            
            if not results:
                dh_log(
                    "Arrr! No results found for the week!",
                    level="WARNING",
                    context={"week_start": week_start.isoformat(), "week_end": week_end.isoformat()}
                )
                return
            
            dh_log(
                f"Arrr! Found {len(results)} winning combinations",
                level="INFO",
                context={"num_combinations": len(results)}
            )
            
            # Store the winning combinations
            for idx, result in enumerate(results, 1):
                main_params = json.loads(result.main_model_params)
                strong_params = json.loads(result.strong_model_params)
                # Add training parameters while preserving existing ones
                if 'training_params' not in main_params:
                    main_params['training_params'] = {}
                main_params['training_params'].update({
                    'train_start_date': str(result.train_start_date) if result.train_start_date else None,
                    'train_end_date': str(result.train_end_date) if result.train_end_date else None,
                    'test_count': int(result.test_count) if result.test_count is not None else None
                })
                
                winning_combo = WeeklyWinningCombination(
                    model_id=result.model_id,
                    strong_model_id=result.strong_model_id,
                    main_model_params=json.dumps(main_params),
                    strong_model_params=json.dumps(strong_params),
                    total_roi=result.total_roi,
                    num_prediction_runs=result.num_prediction_runs,
                    num_tickets=result.num_tickets,
                    total_cost=result.total_cost,
                    total_prize=result.total_prize,
                    week_start_date=week_start,
                    week_end_date=week_end
                )
                db.add(winning_combo)
                dh_log(
                    f"Arrr! Stored winning combination #{idx}",
                    level="INFO",
                    context={
                        "position": idx,
                        "model_id": result.model_id,
                        "strong_model_id": result.strong_model_id,
                        "total_roi": result.total_roi,
                        "num_tickets": result.num_tickets,
                        "total_prize": result.total_prize,
                        "main_params": main_params,
                        "strong_params": strong_params,
                        "training_params": main_params['training_params']
                    }
                )
            
            db.commit()
            
            end_time = datetime.datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            dh_log(
                "Arrr! Weekly winning combinations update completed successfully!",
                level="INFO",
                context={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "num_combinations": len(results)
                }
            )
            
    except Exception as e:
        end_time = datetime.datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        error_traceback = traceback.format_exc()
        
        dh_log(
            "Arrr! Weekly winning combinations update failed!",
            level="ERROR",
            context={
                "error": str(e),
                "traceback": error_traceback,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration
            }
        )
        raise

if __name__ == "__main__":
    update_weekly_winning_combinations() 