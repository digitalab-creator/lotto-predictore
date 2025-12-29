"""
Validation utilities for grid search service.
Praisin' the FSM! 🍝⚓
"""
from typing import Dict, Any, List
from shared.logging_service import get_backend_logger

logger = get_backend_logger()

REQUIRED_PARAMS = ['top_n', 'num_to_recommend', 'test_count', 'main_algo', 'strong_algo']


class GridSearchValidator:
    """Validator for grid search results and parameters"""
    
    @staticmethod
    def validate_grid_results_format(grid_results: Any, quick_mode: bool, use_cache: bool, draws_count: int) -> None:
        """Validate that grid_results is a dict"""
        if not isinstance(grid_results, dict):
            error_details = {
                "expected_type": "dict",
                "actual_type": type(grid_results).__name__,
                "actual_value": str(grid_results)[:500],
                "quick_mode": quick_mode,
                "use_cache": use_cache,
                "draws_count": draws_count
            }
            logger.error(
                f"Arrr! Grid search returned invalid format! Expected dict, got {type(grid_results).__name__}",
                context=error_details
            )
            raise ValueError(
                f"Grid search returned invalid format: expected dict, got {type(grid_results).__name__}. "
                f"Result: {str(grid_results)[:200]}"
            )
    
    @staticmethod
    def validate_no_error_in_results(grid_results: Dict[str, Any]) -> None:
        """Validate that grid_results doesn't contain an error"""
        if 'error' in grid_results:
            error_msg = (
                f"Grid search failed with error: {grid_results['error']}. "
                f"Cannot generate optimized parameters without successful grid search."
            )
            logger.error(
                "Arrr! Grid search failed!",
                context={
                    "error": grid_results['error'],
                    "grid_results_keys": list(grid_results.keys()) if isinstance(grid_results, dict) else "N/A"
                }
            )
            raise ValueError(error_msg)
    
    @staticmethod
    def validate_best_params_type(best_params: Any, grid_results: Dict[str, Any]) -> None:
        """Validate that best_params is a dict"""
        if not isinstance(best_params, dict):
            error_msg = (
                f"best_parameters is not a dict: got {type(best_params).__name__} instead. "
                f"This may indicate corrupted cache. Value: {str(best_params)[:500]}. "
                f"Grid results keys: {list(grid_results.keys()) if isinstance(grid_results, dict) else 'N/A'}"
            )
            logger.error(
                "Arrr! best_parameters has invalid type!",
                context={
                    "expected_type": "dict",
                    "actual_type": type(best_params).__name__,
                    "best_params_value": str(best_params)[:500],
                    "grid_results_type": type(grid_results).__name__,
                    "grid_results_keys": list(grid_results.keys()) if isinstance(grid_results, dict) else "N/A"
                }
            )
            raise ValueError(error_msg)
    
    @staticmethod
    def validate_best_params_not_empty(best_params: Dict[str, Any], grid_results: Dict[str, Any]) -> None:
        """Validate that best_params is not empty"""
        if not best_params:
            error_msg = (
                f"best_parameters is empty dict. Grid search completed but found no valid results. "
                f"Grid results: {str(grid_results)[:500]}"
            )
            logger.error(
                "Arrr! No best parameters found in grid search results!",
                context={
                    "grid_results": grid_results,
                    "grid_results_type": type(grid_results).__name__,
                    "grid_results_keys": list(grid_results.keys()) if isinstance(grid_results, dict) else "N/A"
                }
            )
            raise ValueError(error_msg)
    
    @staticmethod
    def validate_params_dict_type(params_dict: Any, best_params: Dict[str, Any]) -> None:
        """Validate that params_dict is a dict"""
        if not isinstance(params_dict, dict):
            error_msg = (
                f"best_params['parameters'] is not a dict: got {type(params_dict).__name__} instead. "
                f"best_params structure: {str(best_params)[:500]}"
            )
            logger.error(
                "Arrr! best_params['parameters'] has invalid type!",
                context={
                    "expected_type": "dict",
                    "actual_type": type(params_dict).__name__,
                    "params_value": str(params_dict)[:500],
                    "best_params_keys": list(best_params.keys()) if isinstance(best_params, dict) else "N/A",
                    "best_params": str(best_params)[:500]
                }
            )
            raise ValueError(error_msg)
    
    @staticmethod
    def validate_params_dict_not_empty(params_dict: Dict[str, Any], best_params: Dict[str, Any]) -> None:
        """Validate that params_dict is not empty"""
        if not params_dict:
            error_msg = (
                f"best_params['parameters'] is empty. best_params structure: {str(best_params)[:500]}"
            )
            logger.error(
                "Arrr! best_params['parameters'] is empty!",
                context={
                    "best_params": best_params,
                    "best_params_keys": list(best_params.keys()) if isinstance(best_params, dict) else "N/A"
                }
            )
            raise ValueError(error_msg)
    
    @staticmethod
    def validate_required_params(params_dict: Dict[str, Any]) -> None:
        """Validate that all required parameters exist"""
        missing_params = [p for p in REQUIRED_PARAMS if p not in params_dict]
        if missing_params:
            error_msg = (
                f"Missing required parameters in params_dict: {missing_params}. "
                f"Available keys: {list(params_dict.keys())}. "
                f"params_dict: {str(params_dict)[:500]}"
            )
            logger.error(
                "Arrr! Missing required parameters in params_dict!",
                context={
                    "missing_params": missing_params,
                    "available_keys": list(params_dict.keys()),
                    "params_dict": str(params_dict)[:500]
                }
            )
            raise ValueError(error_msg)
    
    @staticmethod
    def validate_roi_exists(best_params: Dict[str, Any]) -> None:
        """Validate that roi exists in best_params"""
        if 'roi' not in best_params:
            error_msg = (
                f"Missing 'roi' in best_params. Available keys: {list(best_params.keys())}. "
                f"best_params: {str(best_params)[:500]}"
            )
            logger.error(
                "Arrr! Missing 'roi' in best_params!",
                context={
                    "available_keys": list(best_params.keys()),
                    "best_params": str(best_params)[:500]
                }
            )
            raise ValueError(error_msg)
    
    @staticmethod
    def validate_all(grid_results: Any, quick_mode: bool, use_cache: bool, draws_count: int) -> Dict[str, Any]:
        """
        Validate all aspects of grid search results and return validated best_params
        """
        GridSearchValidator.validate_grid_results_format(grid_results, quick_mode, use_cache, draws_count)
        GridSearchValidator.validate_no_error_in_results(grid_results)
        
        best_params = grid_results.get('best_parameters', {})
        GridSearchValidator.validate_best_params_type(best_params, grid_results)
        GridSearchValidator.validate_best_params_not_empty(best_params, grid_results)
        
        params_dict = best_params.get('parameters', {})
        GridSearchValidator.validate_params_dict_type(params_dict, best_params)
        GridSearchValidator.validate_params_dict_not_empty(params_dict, best_params)
        GridSearchValidator.validate_required_params(params_dict)
        GridSearchValidator.validate_roi_exists(best_params)
        
        return best_params

