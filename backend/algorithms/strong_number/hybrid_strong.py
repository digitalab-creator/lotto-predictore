from typing import List, Dict, Any
from models import Draw
from .base import StrongNumberAlgorithm, register_strong_algorithm, STRONG_NUMBER_REGISTRY
from algorithms.base import ALGORITHM_REGISTRY
import random
from collections import Counter
from shared.logging_service import get_backend_logger

logger = get_backend_logger()

@register_strong_algorithm
class HybridStrongNumber(StrongNumberAlgorithm):
    """Combines main algorithm insights with strong-specific logic for optimal performance"""
    version = "hybrid_main_strong"
    description = "Hybrid approach combining top main algorithms with traditional strong algorithms"

    def predict(self, draws: List[Draw], **kwargs) -> int:
        logger.debug(
            "HybridStrongNumber predict called",
            context={
                "num_draws": len(draws),
                "available_main_algos": len(ALGORITHM_REGISTRY),
                "available_strong_algos": len(STRONG_NUMBER_REGISTRY)
            }
        )
        
        # Get insights from top performing main algorithms
        main_insights = []
        
        # Use top performing main algorithms (based on your logs showing good performance)
        top_main_algos = [
            "sequence_lstm_classifier_gridsearch",
            "recency_weighted_linear", 
            "random_from_top15_pool",
            "top_n_frequent_per_position_v1",
            "sequence_lstm_classifier_h128_l2"
        ]
        
        for algo_name in top_main_algos:
            if algo_name in ALGORITHM_REGISTRY:
                try:
                    algo_class = ALGORITHM_REGISTRY[algo_name]
                    algo = algo_class()
                    results = algo.run(draws, top_n=1, num_to_recommend=1)
                    if results and 'numbers' in results[0]:
                        main_number = results[0]['numbers'][0]
                        strong_number = ((main_number - 1) % 7) + 1
                        main_insights.append(strong_number)
                        
                        logger.debug(
                            f"Main algorithm {algo_name} suggested strong number {strong_number}",
                            context={
                                "main_algorithm": algo_name,
                                "main_number": main_number,
                                "strong_number": strong_number
                            }
                        )
                except Exception as e:
                    logger.warning(
                        f"Main algorithm {algo_name} failed in hybrid",
                        context={
                            "main_algorithm": algo_name,
                            "error": str(e)
                        }
                    )
                    continue
        
        # Combine with traditional strong algorithms
        traditional_strong = []
        traditional_algos = ["most_common", "recency_weighted", "random"]
        
        for strong_name in traditional_algos:
            if strong_name in STRONG_NUMBER_REGISTRY:
                try:
                    strong_class = STRONG_NUMBER_REGISTRY[strong_name]
                    strong_algo = strong_class()
                    strong_number = strong_algo.predict(draws)
                    traditional_strong.append(strong_number)
                    
                    logger.debug(
                        f"Traditional strong algorithm {strong_name} suggested {strong_number}",
                        context={
                            "strong_algorithm": strong_name,
                            "strong_number": strong_number
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Traditional strong algorithm {strong_name} failed in hybrid",
                        context={
                            "strong_algorithm": strong_name,
                            "error": str(e)
                        }
                    )
                    continue
        
        # Combine all insights
        all_insights = main_insights + traditional_strong
        
        if all_insights:
            # Use weighted voting: main algorithms get 2x weight
            weighted_insights = []
            weighted_insights.extend(main_insights * 2)  # Main algorithms get double weight
            weighted_insights.extend(traditional_strong)
            
            counter = Counter(weighted_insights)
            most_common = counter.most_common(1)[0][0]
            
            logger.info(
                f"Hybrid strong number prediction: {most_common}",
                context={
                    "main_insights": main_insights,
                    "traditional_strong": traditional_strong,
                    "weighted_counter": dict(counter),
                    "final_choice": most_common
                }
            )
            
            self._validate_strong_number(most_common)
            return most_common
        
        # Ultimate fallback
        fallback = random.randint(1, 7)
        logger.warning(
            f"No insights available, using random fallback: {fallback}",
            context={
                "main_insights_count": len(main_insights),
                "traditional_strong_count": len(traditional_strong),
                "fallback": fallback
            }
        )
        return fallback

@register_strong_algorithm
class EnsembleStrongNumber(StrongNumberAlgorithm):
    """Ensemble approach using multiple main algorithms with equal voting"""
    version = "ensemble_main_strong"
    description = "Ensemble of multiple main algorithms with equal voting for strong number prediction"

    def predict(self, draws: List[Draw], **kwargs) -> int:
        logger.debug(
            "EnsembleStrongNumber predict called",
            context={"num_draws": len(draws)}
        )
        
        # Use a diverse set of main algorithms
        ensemble_algos = [
            "sequence_lstm_classifier_gridsearch",
            "recency_weighted_linear",
            "random_from_top15_pool", 
            "top_n_frequent_per_position_v1",
            "balanced_spread_fixed_ranges",
            "delta_system_data_driven"
        ]
        
        ensemble_results = []
        
        for algo_name in ensemble_algos:
            if algo_name in ALGORITHM_REGISTRY:
                try:
                    algo_class = ALGORITHM_REGISTRY[algo_name]
                    algo = algo_class()
                    results = algo.run(draws, top_n=1, num_to_recommend=1)
                    if results and 'numbers' in results[0]:
                        main_number = results[0]['numbers'][0]
                        strong_number = ((main_number - 1) % 7) + 1
                        ensemble_results.append(strong_number)
                        
                        logger.debug(
                            f"Ensemble member {algo_name} voted for {strong_number}",
                            context={
                                "ensemble_member": algo_name,
                                "vote": strong_number
                            }
                        )
                except Exception as e:
                    logger.warning(
                        f"Ensemble member {algo_name} failed",
                        context={
                            "ensemble_member": algo_name,
                            "error": str(e)
                        }
                    )
                    continue
        
        if ensemble_results:
            # Simple majority voting
            counter = Counter(ensemble_results)
            most_common = counter.most_common(1)[0][0]
            
            logger.info(
                f"Ensemble strong number prediction: {most_common}",
                context={
                    "ensemble_votes": ensemble_results,
                    "vote_counts": dict(counter),
                    "final_choice": most_common
                }
            )
            
            self._validate_strong_number(most_common)
            return most_common
        
        # Fallback
        fallback = random.randint(1, 7)
        logger.warning(f"Ensemble failed, using random fallback: {fallback}")
        return fallback

