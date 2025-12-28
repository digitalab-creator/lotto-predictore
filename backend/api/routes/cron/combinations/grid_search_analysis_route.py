from fastapi import APIRouter, HTTPException
from services.core.cron_tracker import CronTracker
from services.core.grid_search_service import WeeklyCombinationsGridSearch
from logger import logger
from .base_combination_generator import get_db_session, load_draws_with_filter
from typing import Dict, Any, List
import time

router = APIRouter()


@router.post("/cron/grid-search-analysis")
async def grid_search_analysis():
    """Run comprehensive grid search analysis for algorithm optimization"""
    start_time = time.time()
    logger.info("Arrr! Starting comprehensive grid search analysis, praisin' the FSM!", context={"start_time": start_time})
    
    # Initialize cron tracking
    db = get_db_session()
    tracker = CronTracker(db)
    cron_job = None
    
    try:
        # Start tracking the job
        cron_job = tracker.start_job(
            job_name="grid-search-analysis",
            job_type="analysis",
            metadata={"start_time": start_time}
        )
        
        try:
            # Get all draws, filtering out strong_number == 8
            draws, filtered_count, draws_time = load_draws_with_filter(db)
            
            logger.info(
                "Arrr! Filtered out draws with strong_number == 8 for grid search analysis, praisin' the FSM!",
                context={
                    "filtered_count": filtered_count, 
                    "total_after_filter": len(draws),
                    "draws_load_time": f"{draws_time:.2f}s"
                }
            )
            
            if len(draws) < 30:
                error_msg = "Not enough draws in database for grid search analysis (need at least 30)."
                logger.error(error_msg)
                if cron_job:
                    tracker.fail_job(cron_job, error_msg, time.time() - start_time)
                return {"status": "error", "message": error_msg}
            
            # Run comprehensive grid search
            grid_search_start = time.time()
            grid_search = WeeklyCombinationsGridSearch(db)
            grid_results = grid_search.run_grid_search(
                draws=draws,
                use_cache=True,
                max_combinations=100,  # More comprehensive analysis
                quick_mode=False  # Full analysis mode
            )
            grid_search_time = time.time() - grid_search_start
            
            logger.info(
                "Arrr! Comprehensive grid search analysis completed",
                context={
                    "total_combinations_tested": grid_results.get('grid_search_metadata', {}).get('total_combinations_tested', 0),
                    "grid_search_time": f"{grid_search_time:.2f}s",
                    "best_roi": grid_results.get('best_parameters', {}).get('roi', 0)
                }
            )
            
            # Analyze results and provide insights
            analysis_start = time.time()
            insights = _analyze_grid_search_results(grid_results)
            analysis_time = time.time() - analysis_start
            
            total_time = time.time() - start_time
            
            # Mark job as completed
            if cron_job:
                tracker.complete_job(cron_job, total_time)
            
            logger.info(
                "Arrr! Grid search analysis completed successfully, praisin' the FSM!",
                context={
                    "total_combinations_tested": grid_results.get('grid_search_metadata', {}).get('total_combinations_tested', 0),
                    "best_roi": grid_results.get('best_parameters', {}).get('roi', 0),
                    "total_time": f"{total_time:.2f}s",
                    "insights_count": len(insights)
                }
            )
            
            return {
                "status": "success",
                "message": "Grid search analysis completed successfully",
                "best_parameters": grid_results.get('best_parameters', {}),
                "insights": insights,
                "performance_breakdown": {
                    "draws_load": f"{draws_time:.2f}s",
                    "grid_search": f"{grid_search_time:.2f}s",
                    "analysis": f"{analysis_time:.2f}s",
                    "total": f"{total_time:.2f}s"
                },
                "metadata": grid_results.get('grid_search_metadata', {})
            }
            
        except Exception as e:
            error_msg = f"Error in grid search analysis: {str(e)}"
            logger.error(
                "Arrr! Error in grid search analysis!",
                context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
            )
            if cron_job:
                tracker.fail_job(cron_job, error_msg, time.time() - start_time)
            db.rollback()
            raise
        finally:
            db.close()
            
    except Exception as e:
        error_msg = f"Error in grid search analysis endpoint: {str(e)}"
        logger.error(
            "Arrr! Error in grid search analysis endpoint!",
            context={"error": str(e), "total_elapsed": f"{time.time() - start_time:.2f}s"}
        )
        if cron_job:
            tracker.fail_job(cron_job, error_msg, time.time() - start_time)
        raise HTTPException(status_code=500, detail=str(e))


def _analyze_grid_search_results(grid_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze grid search results and provide insights"""
    insights = []
    all_results = grid_results.get('all_results', [])
    best_params = grid_results.get('best_parameters', {})
    
    if not all_results:
        insights.append({
            "type": "error",
            "message": "No results to analyze",
            "severity": "high"
        })
        return insights
    
    # Analyze parameter performance
    param_performance = {}
    for result in all_results:
        params = result.get('parameters', {})
        roi = result.get('roi', 0)
        
        # Track top_n performance
        top_n = params.get('top_n', 0)
        if top_n not in param_performance:
            param_performance[top_n] = []
        param_performance[top_n].append(roi)
        
        # Track num_to_recommend performance
        num_rec = params.get('num_to_recommend', 0)
        if f"num_rec_{num_rec}" not in param_performance:
            param_performance[f"num_rec_{num_rec}"] = []
        param_performance[f"num_rec_{num_rec}"].append(roi)
        
        # Track test_count performance
        test_count = params.get('test_count', 0)
        if f"test_count_{test_count}" not in param_performance:
            param_performance[f"test_count_{test_count}"] = []
        param_performance[f"test_count_{test_count}"].append(roi)
    
    # Find best performing parameters
    for param_name, rois in param_performance.items():
        if rois:
            avg_roi = sum(rois) / len(rois)
            max_roi = max(rois)
            insights.append({
                "type": "parameter_analysis",
                "parameter": param_name,
                "average_roi": avg_roi,
                "max_roi": max_roi,
                "sample_size": len(rois),
                "recommendation": f"Best {param_name}: {max_roi:.4f} ROI"
            })
    
    # Analyze algorithm combinations
    algo_performance = {}
    for result in all_results:
        main_algo = result.get('main_algo', '')
        strong_algo = result.get('strong_algo', '')
        roi = result.get('roi', 0)
        
        combo_key = f"{main_algo}+{strong_algo}"
        if combo_key not in algo_performance:
            algo_performance[combo_key] = []
        algo_performance[combo_key].append(roi)
    
    # Find top algorithm combinations
    top_combos = sorted(algo_performance.items(), key=lambda x: max(x[1]), reverse=True)[:5]
    for combo, rois in top_combos:
        insights.append({
            "type": "algorithm_combination",
            "combination": combo,
            "best_roi": max(rois),
            "average_roi": sum(rois) / len(rois),
            "sample_size": len(rois),
            "recommendation": f"Top performing combo: {combo}"
        })
    
    # Overall insights
    if best_params:
        insights.append({
            "type": "best_overall",
            "message": "Best overall configuration found",
            "best_roi": best_params.get('roi', 0),
            "parameters": best_params.get('parameters', {}),
            "recommendation": "Use these parameters for optimal performance"
        })
    
    return insights

