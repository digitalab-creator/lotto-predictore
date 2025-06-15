from typing import Dict, Any
from logger import logger

def print_combo_index_insights(results: Dict[str, Any]) -> None:
    """
    Print insights about combo indices from simulation results.
    
    Args:
        results (Dict[str, Any]): Simulation results dictionary
    """
    logger.info("Arrr! Combo Index Insights:")
    for (main_version, strong_version), result in results.items():
        logger.info(f"Main: {main_version}, Strong: {strong_version}")
        for date_entry in result.get('dates', []):
            logger.info(
                f"Date: {date_entry['test_draw_date']}",
                context={
                    "max_hits": date_entry['max_hits'],
                    "any_strong_hit": date_entry['any_strong_hit'],
                    "total_prize": date_entry['total_prize']
                }
            )

def print_table_summary(results: Dict[str, Any]) -> None:
    """
    Print summary of simulation results.
    
    Args:
        results (Dict[str, Any]): Simulation results dictionary
    """
    logger.info("Arrr! Table Summary:")
    for (main_version, strong_version), result in results.items():
        logger.info(
            f"Main: {main_version}, Strong: {strong_version}",
            context={
                "roi": result['roi'],
                "total_prize": result['total_prize'],
                "total_cost": result['total_cost'],
                "test_count": result['test_count']
            }
        ) 