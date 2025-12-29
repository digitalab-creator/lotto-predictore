import itertools
import time
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models import Draw

# Set up backend path using utility function
from utils.path_setup import setup_backend_path
setup_backend_path()

from shared.logging_service import get_backend_logger
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from services.core.simulation_engine import SimulationEngine
from services.core.grid_search_validator import GridSearchValidator
from services.core.grid_search_cache import GridSearchCache
from config import NUM_COMBINATIONS_TO_RECOMMEND

logger = get_backend_logger()

class WeeklyCombinationsGridSearch:
    """
    Grid search service for optimizing weekly combinations generation parameters.
    Praisin' the FSM! 🍝⚓
    """
    
    def __init__(self, db: Session, cache_ttl: int = 7 * 24 * 60 * 60):
        """
        Initialize grid search service
        
        Args:
            db: Database session
            cache_ttl: Cache TTL in seconds (default: 7 days)
        """
        self.db = db
        self.cache = GridSearchCache(cache_ttl)
        self.engine = SimulationEngine(db)
        
        # Define parameter grids for optimization
        self.parameter_grids = {
            'top_n_values': [2, 3, 4, 5, 6],
            'num_to_recommend_values': [3, 5, 8, 10, 12],
            'test_split_ratios': [8, 10, 12, 15, 18],  # Number of draws for test set
            'algorithm_combinations': self._get_balanced_algorithm_combinations()
        }
        
        logger.info(
            "Arrr! Weekly Combinations Grid Search initialized, praisin' the FSM!",
            context={
                "cache_ttl": cache_ttl,
                "parameter_grids": {k: len(v) for k, v in self.parameter_grids.items()}
            }
        )
    
    def _get_balanced_algorithm_combinations(self) -> List[Dict[str, str]]:
        """Get a balanced set of algorithm combinations for testing"""
        # Get top performing algorithms from registry
        main_algorithms = list(ALGORITHM_REGISTRY.keys())[:8]  # Limit to top 8 for performance
        strong_algorithms = list(STRONG_NUMBER_REGISTRY.keys())
        
        combinations = []
        for main_algo in main_algorithms:
            for strong_algo in strong_algorithms:
                combinations.append({
                    'main_algo': main_algo,
                    'strong_algo': strong_algo
                })
        
        return combinations
    
    
    def run_grid_search(
        self, 
        draws: List[Draw], 
        use_cache: bool = True,
        max_combinations: int = 50,
        quick_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Run comprehensive grid search for weekly combinations optimization
        
        Args:
            draws: Historical lottery draws
            use_cache: Whether to use cached results
            max_combinations: Maximum number of parameter combinations to test
            quick_mode: If True, test fewer combinations for faster execution
        
        Returns:
            Dictionary with best parameters and all results
        """
        start_time = time.time()
        
        logger.info(
            "Arrr! Starting comprehensive grid search for weekly combinations, praisin' the FSM!",
            context={
                "total_draws": len(draws),
                "use_cache": use_cache,
                "max_combinations": max_combinations,
                "quick_mode": quick_mode
            }
        )
        
        # Filter draws (same logic as weekly combinations)
        filtered_draws = [d for d in draws if d.strong_number <= 7]
        filtered_count = len(draws) - len(filtered_draws)
        
        logger.info(
            "Arrr! Filtered draws for grid search",
            context={
                "original_count": len(draws),
                "filtered_count": filtered_count,
                "remaining_count": len(filtered_draws)
            }
        )
        
        if len(filtered_draws) < 30:
            error_msg = "Not enough draws for grid search (need at least 30)"
            logger.error(error_msg)
            return {"error": error_msg}
        
        # Create grid search parameters
        grid_params = self._create_grid_parameters(quick_mode, max_combinations)
        cache_key = self.cache.get_cache_key(filtered_draws, grid_params)
        
        # Check cache first
        if use_cache:
            cached_results = self.cache.load_from_cache(cache_key)
            if cached_results:
                return cached_results
        
        # Run grid search
        results = self._execute_grid_search(filtered_draws, grid_params)
        
        # Find best parameters
        best_result = self._find_best_result(results)
        
        # Prepare final results
        final_results = {
            "best_parameters": best_result,
            "all_results": results,
            "grid_search_metadata": {
                "total_combinations_tested": len(results),
                "execution_time": time.time() - start_time,
                "cache_key": cache_key,
                "draws_used": len(filtered_draws),
                "quick_mode": quick_mode
            }
        }
        
        # Save to cache
        if use_cache:
            self.cache.save_to_cache(cache_key, final_results)
        
        logger.info(
            "Arrr! Grid search completed successfully, praisin' the FSM!",
            context={
                "best_roi": best_result.get('roi', 0),
                "best_params": best_result.get('parameters', {}),
                "total_combinations": len(results),
                "execution_time": f"{time.time() - start_time:.2f}s"
            }
        )
        
        return final_results
    
    def _create_grid_parameters(self, quick_mode: bool, max_combinations: int) -> List[Dict[str, Any]]:
        """Create parameter combinations for grid search"""
        if quick_mode:
            # Quick mode: test fewer combinations
            quick_grid = {
                'top_n_values': [3, 5],
                'num_to_recommend_values': [5, 8],
                'test_split_ratios': [10, 12],
                'algorithm_combinations': self.parameter_grids['algorithm_combinations'][:4]  # Only first 4
            }
        else:
            quick_grid = self.parameter_grids
        
        # Generate all combinations
        all_combinations = list(itertools.product(
            quick_grid['top_n_values'],
            quick_grid['num_to_recommend_values'],
            quick_grid['test_split_ratios'],
            quick_grid['algorithm_combinations']
        ))
        
        # Limit combinations if needed
        if len(all_combinations) > max_combinations:
            # Use stratified sampling to get diverse combinations
            step = len(all_combinations) // max_combinations
            all_combinations = all_combinations[::step][:max_combinations]
        
        # Convert to parameter dictionaries
        parameter_combinations = []
        for idx, combo_tuple in enumerate(all_combinations):
            try:
                top_n, num_to_recommend, test_count, algo_combo = combo_tuple
                
                # Validate algo_combo is a dict
                if not isinstance(algo_combo, dict):
                    error_msg = (
                        f"Invalid algorithm combination at index {idx}: expected dict, got {type(algo_combo).__name__}. "
                        f"Value: {str(algo_combo)[:200]}. "
                        f"This indicates algorithm_combinations contains non-dict items."
                    )
                    logger.error(
                        "Arrr! Invalid algorithm combination format in _create_grid_parameters!",
                        context={
                            "index": idx,
                            "expected_type": "dict",
                            "actual_type": type(algo_combo).__name__,
                            "value": str(algo_combo)[:200],
                            "combo_tuple": str(combo_tuple)[:200],
                            "algorithm_combinations_type": type(self.parameter_grids['algorithm_combinations']).__name__,
                            "algorithm_combinations_length": len(self.parameter_grids['algorithm_combinations']) if isinstance(self.parameter_grids['algorithm_combinations'], list) else "N/A"
                        }
                    )
                    raise ValueError(error_msg)
                
                # Validate required keys exist
                if 'main_algo' not in algo_combo or 'strong_algo' not in algo_combo:
                    error_msg = (
                        f"Algorithm combination at index {idx} missing required keys. "
                        f"Expected 'main_algo' and 'strong_algo', got keys: {list(algo_combo.keys())}. "
                        f"Value: {str(algo_combo)[:200]}"
                    )
                    logger.error(
                        "Arrr! Algorithm combination missing required keys!",
                        context={
                            "index": idx,
                            "expected_keys": ["main_algo", "strong_algo"],
                            "actual_keys": list(algo_combo.keys()),
                            "algo_combo": str(algo_combo)[:200]
                        }
                    )
                    raise ValueError(error_msg)
                
                parameter_combinations.append({
                    'top_n': top_n,
                    'num_to_recommend': num_to_recommend,
                    'test_count': test_count,
                    'main_algo': algo_combo['main_algo'],
                    'strong_algo': algo_combo['strong_algo']
                })
            except (ValueError, TypeError, KeyError) as e:
                error_msg = (
                    f"Error processing combination at index {idx}: {str(e)}. "
                    f"Combination tuple: {str(combo_tuple)[:200]}"
                )
                logger.error(
                    "Arrr! Error processing combination in _create_grid_parameters!",
                    context={
                        "index": idx,
                        "error": str(e),
                        "combo_tuple": str(combo_tuple)[:200],
                        "combo_tuple_type": type(combo_tuple).__name__,
                        "combo_tuple_length": len(combo_tuple) if hasattr(combo_tuple, '__len__') else "N/A"
                    }
                )
                raise ValueError(error_msg) from e
        
        logger.info(
            "Arrr! Created parameter combinations for grid search",
            context={
                "total_combinations": len(parameter_combinations),
                "quick_mode": quick_mode,
                "max_combinations": max_combinations
            }
        )
        
        return parameter_combinations
    
    def _execute_grid_search(self, draws: List[Draw], grid_params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute the actual grid search"""
        results = []
        total_combinations = len(grid_params)
        
        for idx, params in enumerate(grid_params, 1):
            combo_start = time.time()
            
            logger.info(
                f"Arrr! Testing combination {idx}/{total_combinations}",
                context={
                    "parameters": params,
                    "progress": f"{idx}/{total_combinations}",
                    "elapsed_time": f"{time.time() - combo_start:.2f}s"
                }
            )
            
            try:
                # Split data based on test_count parameter
                test_count = params['test_count']
                if len(draws) < test_count + 10:  # Need at least 10 draws for training
                    logger.warning(
                        f"Arrr! Skipping combination due to insufficient data",
                        context={
                            "test_count": test_count,
                            "total_draws": len(draws),
                            "parameters": params
                        }
                    )
                    continue
                
                train_draws = draws[:-test_count]
                test_draws = draws[-test_count:]
                train_start = train_draws[0].date
                train_end = train_draws[-1].date
                
                # Run simulation with current parameters
                simulation_results = self.engine.run_comparison(
                    train_start=train_start,
                    train_end=train_end,
                    test_count=test_count,
                    top_n=params['top_n'],
                    algo_names=[params['main_algo']],
                    strong_algo_names=[params['strong_algo']]
                )
                
                # Validate simulation_results format
                if not isinstance(simulation_results, dict):
                    error_details = {
                        "expected_type": "dict",
                        "actual_type": type(simulation_results).__name__,
                        "actual_value": str(simulation_results)[:500],
                        "parameters": params,
                        "train_start": str(train_start),
                        "train_end": str(train_end),
                        "test_count": test_count
                    }
                    logger.error(
                        f"Arrr! run_comparison returned invalid format! Expected dict, got {type(simulation_results).__name__}",
                        context=error_details
                    )
                    raise ValueError(
                        f"run_comparison returned invalid format: expected dict, got {type(simulation_results).__name__}. "
                        f"Parameters: {params}, Result: {str(simulation_results)[:200]}"
                    )
                
                # Extract results
                for (main_algo, strong_algo), result in simulation_results.items():
                    result_with_params = {
                        'parameters': params,
                        'roi': result['roi'],
                        'total_prize': result['total_prize'],
                        'total_cost': result['total_cost'],
                        'test_count': test_count,
                        'train_start': train_start,
                        'train_end': train_end,
                        'main_algo': main_algo,
                        'strong_algo': strong_algo,
                        'execution_time': time.time() - combo_start
                    }
                    results.append(result_with_params)
                
                combo_time = time.time() - combo_start
                logger.info(
                    f"Arrr! Completed combination {idx}/{total_combinations}",
                    context={
                        "parameters": params,
                        "roi": result['roi'],
                        "execution_time": f"{combo_time:.2f}s"
                    }
                )
                
            except Exception as e:
                combo_time = time.time() - combo_start
                logger.error(
                    f"Arrr! Failed combination {idx}/{total_combinations}",
                    context={
                        "parameters": params,
                        "error": str(e),
                        "execution_time": f"{combo_time:.2f}s"
                    }
                )
                continue
        
        return results
    
    def _find_best_result(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find the best result based on ROI"""
        if not results:
            return {}
        
        best_result = max(results, key=lambda x: x['roi'])
        
        logger.info(
            "Arrr! Found best grid search result, praisin' the FSM!",
            context={
                "best_roi": best_result['roi'],
                "best_parameters": best_result['parameters'],
                "total_results": len(results)
            }
        )
        
        return best_result
    
    def get_optimized_parameters(
        self, 
        draws: List[Draw], 
        quick_mode: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get optimized parameters for weekly combinations generation
        
        Returns:
            Dictionary with optimized parameters ready for use
        """
        grid_results = self.run_grid_search(
            draws=draws,
            use_cache=use_cache,
            max_combinations=30 if quick_mode else 100,
            quick_mode=quick_mode
        )
        
        # Validate all aspects of grid search results
        best_params = GridSearchValidator.validate_all(
            grid_results, quick_mode, use_cache, len(draws)
        )
        
        # Extract validated parameters
        params_dict = best_params['parameters']
        
        # Return optimized parameters in the format expected by weekly combinations
        optimized_params = {
            'top_n': params_dict['top_n'],
            'num_to_recommend': params_dict['num_to_recommend'],
            'test_count': params_dict['test_count'],
            'main_algo': params_dict['main_algo'],
            'strong_algo': params_dict['strong_algo'],
            'expected_roi': best_params['roi'],
            'grid_search_metadata': grid_results.get('grid_search_metadata', {})
        }
        
        logger.info(
            "Arrr! Returning optimized parameters, praisin' the FSM!",
            context={"optimized_params": optimized_params}
        )
        
        return optimized_params

