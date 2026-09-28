import datetime
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from db import SessionLocal
from models.weekly_winning_combination import WeeklyWinningCombination
from logger import logger
from services.draw_prize import ticket_cost_sql_literal
import traceback
import json

def update_weekly_winning_combinations():
    """
    Updates the top 5 winning model combinations for the current week.
    This should be run once per week.
    """
    from services.weekly_jobs_gate import weekly_email_and_jobs_enabled

    if not weekly_email_and_jobs_enabled():
        logger.info(
            "Arrr! Weekly winning combinations update skipped — "
            "WEEKLY_EMAIL_AND_JOBS_ENABLED is false"
        )
        return
    start_time = datetime.datetime.utcnow()
    logger.info(
        "Arrr! Starting weekly winning combinations update! Praisin' the FSM!",
        context={"start_time": start_time.isoformat()}
    )
    
    try:
        # Calculate week start and end dates
        today = datetime.date.today()
        week_start = today - datetime.timedelta(days=today.weekday())
        week_end = week_start + datetime.timedelta(days=6)
        
        logger.info(
            "Arrr! Processing week range",
            context={"week_start": week_start.isoformat(), "week_end": week_end.isoformat()}
        )
        
        with SessionLocal() as db:
            # Delete existing combinations for this week
            deleted = db.query(WeeklyWinningCombination).filter(
                WeeklyWinningCombination.week_start_date == week_start,
                WeeklyWinningCombination.week_end_date == week_end
            ).delete()
            
            logger.info(
                f"Arrr! Deleted {deleted} existing combinations for this week",
                context={"deleted_count": deleted}
            )
            
            # First check if we have any data in the date range
            check_query = text("""
                SELECT COUNT(*) as count
                FROM prediction_details d
                WHERE d.test_draw_date BETWEEN :week_start AND :week_end
            """)
            
            count_result = db.execute(check_query, {"week_start": week_start, "week_end": week_end}).scalar()
            cost = ticket_cost_sql_literal()
            
            if count_result == 0:
                logger.warning(
                    "Arrr! No prediction details found for this week, using all-time data instead!",
                    context={"week_start": week_start.isoformat(), "week_end": week_end.isoformat()}
                )
                # Use all-time data if no data for this week
                query = text(f"""
                    SELECT
                        p.model_id,
                        p.strong_model_id,
                        p.main_model_params::text AS main_model_params,
                        p.strong_model_params::text AS strong_model_params,
                        ROUND(SUM(d.prize)::numeric / NULLIF(COUNT(d.id) * {cost}, 0)::numeric - 1, 4) AS total_roi,
                        COUNT(DISTINCT p.id) AS num_prediction_runs,
                        COUNT(d.id) AS num_tickets,
                        ROUND((COUNT(d.id) * {cost})::numeric, 2) AS total_cost,
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
                logger.info(
                    f"Arrr! Found {count_result} prediction details for this week!",
                    context={"week_start": week_start.isoformat(), "week_end": week_end.isoformat()}
                )
                # Use weekly data
                query = text(f"""
                    SELECT
                        p.model_id,
                        p.strong_model_id,
                        p.main_model_params::text AS main_model_params,
                        p.strong_model_params::text AS strong_model_params,
                        ROUND(SUM(d.prize)::numeric / NULLIF(COUNT(d.id) * {cost}, 0)::numeric - 1, 4) AS total_roi,
                        COUNT(DISTINCT p.id) AS num_prediction_runs,
                        COUNT(d.id) AS num_tickets,
                        ROUND((COUNT(d.id) * {cost})::numeric, 2) AS total_cost,
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
                logger.warning(
                    "Arrr! No results found for the week!",
                    context={"week_start": week_start.isoformat(), "week_end": week_end.isoformat()}
                )
                return
            
            logger.info(
                f"Arrr! Found {len(results)} winning combinations",
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
                logger.info(
                    f"Arrr! Stored winning combination #{idx}",
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
            
            logger.info(
                "Arrr! Weekly winning combinations update completed successfully!",
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
        
        logger.error(
            "Arrr! Weekly winning combinations update failed!",
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