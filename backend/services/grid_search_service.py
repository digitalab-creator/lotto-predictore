import itertools
import time
import pickle
import hashlib
import os
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from models import Draw
from pathlib import Path

# Set up backend path using utility function
from utils.path_setup import setup_backend_path
setup_backend_path()

from shared.logging_service import get_backend_logger
from algorithms.base import ALGORITHM_REGISTRY
from algorithms.strong_number import STRONG_NUMBER_REGISTRY
from services.simulation_engine import SimulationEngine
from config import NUM_COMBINATIONS_TO_RECOMMEND

logger = get_backend_logger()

class WeeklyCombinationsGridSearch:
    """
    Grid search service for optimizing weekly combinations generation parameters.
    Praisin' the FSM! 🍝⚓
    """
    
    def __init__(self, db: Session, cache_dir: str = "/tmp/grid_search_cache"):
        self.db = db
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
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
                "cache_dir": str(self.cache_dir),
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
    
    def _get_cache_key(self, draws: List[Draw], grid_params: Dict[str, Any]) -> str:
        """Generate cache key for grid search results"""
        # Create hash from draw dates and grid parameters
        draw_dates = ','.join(str(d.date) for d in draws[-50:])  # Use last 50 draws for cache key
        params_str = str(sorted(grid_params.items()))
        key_string = f"{draw_dates}_{params_str}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load grid search results from cache"""
        cache_file = self.cache_dir / f"grid_search_{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                logger.info(
                    "Arrr! Loaded grid search results from cache, praisin' the FSM!",
                    context={"cache_key": cache_key, "cached_results": len(cached_data.get('results', []))}
                )
                return cached_data
            except Exception as e:
                logger.warning(
                    "Arrr! Failed to load from cache, will recompute",
                    context={"cache_key": cache_key, "error": str(e)}
                )
        return None
    
    def _save_to_cache(self, cache_key: str, results: Dict[str, Any]):
        """Save grid search results to cache"""
        cache_file = self.cache_dir / f"grid_search_{cache_key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(results, f)
            logger.info(
                "Arrr! Saved grid search results to cache, praisin' the FSM!",
                context={"cache_key": cache_key, "results_count": len(results.get('results', []))}
            )
        except Exception as e:
            logger.error(
                "Arrr! Failed to save to cache",
                context={"cache_key": cache_key, "error": str(e)}
            )
    
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
        cache_key = self._get_cache_key(filtered_draws, grid_params)
        
        # Check cache first
        if use_cache:
            cached_results = self._load_from_cache(cache_key)
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
            self._save_to_cache(cache_key, final_results)
        
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
        for top_n, num_to_recommend, test_count, algo_combo in all_combinations:
            parameter_combinations.append({
                'top_n': top_n,
                'num_to_recommend': num_to_recommend,
                'test_count': test_count,
                'main_algo': algo_combo['main_algo'],
                'strong_algo': algo_combo['strong_algo']
            })
        
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
        
        if 'error' in grid_results:
            logger.error(
                "Arrr! Grid search failed, using default parameters",
                context={"error": grid_results['error']}
            )
            return self._get_default_parameters()
        
        best_params = grid_results.get('best_parameters', {})
        if not best_params:
            logger.warning(
                "Arrr! No best parameters found, using defaults",
                context={"grid_results": grid_results}
            )
            return self._get_default_parameters()
        
        # Return optimized parameters in the format expected by weekly combinations
        optimized_params = {
            'top_n': best_params.get('parameters', {}).get('top_n', 3),
            'num_to_recommend': best_params.get('parameters', {}).get('num_to_recommend', NUM_COMBINATIONS_TO_RECOMMEND),
            'test_count': best_params.get('parameters', {}).get('test_count', 12),
            'main_algo': best_params.get('parameters', {}).get('main_algo', 'most_common'),
            'strong_algo': best_params.get('parameters', {}).get('strong_algo', 'random'),
            'expected_roi': best_params.get('roi', 0),
            'grid_search_metadata': grid_results.get('grid_search_metadata', {})
        }
        
        logger.info(
            "Arrr! Returning optimized parameters, praisin' the FSM!",
            context={"optimized_params": optimized_params}
        )
        
        return optimized_params
    
    def _get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameters as fallback"""
        return {
            'top_n': 3,
            'num_to_recommend': NUM_COMBINATIONS_TO_RECOMMEND,
            'test_count': 12,
            'main_algo': 'most_common',
            'strong_algo': 'random',
            'expected_roi': 0,
            'grid_search_metadata': {'note': 'Using default parameters - grid search failed'}
        }

