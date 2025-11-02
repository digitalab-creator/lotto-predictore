from typing import List, Dict, Any
from models import Draw
from .base import StrongNumberAlgorithm, register_strong_algorithm
from algorithms.base import ALGORITHM_REGISTRY
import random
from collections import Counter
from shared.logging_service import get_backend_logger

logger = get_backend_logger()

class MainAlgorithmStrongAdapter(StrongNumberAlgorithm):
    """Base adapter to use main algorithms for strong number prediction"""
    
    def __init__(self, main_algorithm_name: str):
        self.main_algorithm_name = main_algorithm_name
        self.main_algo_class = ALGORITHM_REGISTRY[main_algorithm_name]
        self.version = f"{main_algorithm_name}_strong"
        self.description = f"Strong number prediction using {main_algorithm_name} algorithm"
    
    def predict(self, draws: List[Draw], **kwargs) -> int:
        logger.debug(
            f"MainAlgorithmStrongAdapter predict called with {self.main_algorithm_name}",
            context={
                "main_algorithm": self.main_algorithm_name,
                "num_draws": len(draws)
            }
        )
        
        # Create instance of main algorithm
        main_algo = self.main_algo_class()
        
        # Run main algorithm with minimal parameters
        try:
            results = main_algo.run(draws, top_n=1, num_to_recommend=1)
            if results and 'numbers' in results[0]:
                # Map main number to strong number range (1-37 -> 1-7)
                main_number = results[0]['numbers'][0]
                strong_number = ((main_number - 1) % 7) + 1
                self._validate_strong_number(strong_number)
                
                logger.info(
                    f"Mapped main number {main_number} to strong number {strong_number}",
                    context={
                        "main_algorithm": self.main_algorithm_name,
                        "main_number": main_number,
                        "strong_number": strong_number
                    }
                )
                return strong_number
        except Exception as e:
            logger.warning(
                f"Main algorithm {self.main_algorithm_name} failed, using fallback",
                context={
                    "main_algorithm": self.main_algorithm_name,
                    "error": str(e)
                }
            )
        
        # Fallback to random
        fallback = random.randint(1, 7)
        logger.debug(f"Using fallback strong number: {fallback}")
        return fallback

class SmartMainAlgorithmStrongAdapter(MainAlgorithmStrongAdapter):
    """Enhanced adapter with smarter mapping strategies"""
    
    def predict(self, draws: List[Draw], **kwargs) -> int:
        logger.debug(
            f"SmartMainAlgorithmStrongAdapter predict called with {self.main_algorithm_name}",
            context={
                "main_algorithm": self.main_algorithm_name,
                "num_draws": len(draws)
            }
        )
        
        main_algo = self.main_algo_class()
        
        try:
            # Get multiple results for better mapping
            results = main_algo.run(draws, top_n=3, num_to_recommend=3)
            
            if results:
                # Strategy: Use most frequent number from all results
                all_numbers = []
                for result in results:
                    if 'numbers' in result:
                        all_numbers.extend(result['numbers'])
                
                if all_numbers:
                    # Count frequency and pick most common
                    counter = Counter(all_numbers)
                    most_common = counter.most_common(1)[0][0]
                    strong_number = ((most_common - 1) % 7) + 1
                    self._validate_strong_number(strong_number)
                    
                    logger.info(
                        f"Smart mapping: most common main number {most_common} -> strong number {strong_number}",
                        context={
                            "main_algorithm": self.main_algorithm_name,
                            "most_common_main": most_common,
                            "strong_number": strong_number,
                            "all_numbers": all_numbers[:10]  # First 10 for context
                        }
                    )
                    return strong_number
                    
        except Exception as e:
            logger.warning(
                f"Smart main algorithm {self.main_algorithm_name} failed, using fallback",
                context={
                    "main_algorithm": self.main_algorithm_name,
                    "error": str(e)
                }
            )
            
        return random.randint(1, 7)

# Register adapters for key algorithms
@register_strong_algorithm
class TopNFrequentStrongNumber(MainAlgorithmStrongAdapter):
    def __init__(self):
        super().__init__("top_n_frequent_per_position_v1")

@register_strong_algorithm  
class RecencyWeightedStrongNumber(MainAlgorithmStrongAdapter):
    def __init__(self):
        super().__init__("recency_weighted_linear")

@register_strong_algorithm
class RandomPoolStrongNumber(MainAlgorithmStrongAdapter):
    def __init__(self):
        super().__init__("random_from_top15_pool")

@register_strong_algorithm
class LSTMStrongNumber(MainAlgorithmStrongAdapter):
    def __init__(self):
        super().__init__("sequence_lstm_classifier")

@register_strong_algorithm
class LSTMGridSearchStrongNumber(MainAlgorithmStrongAdapter):
    def __init__(self):
        super().__init__("sequence_lstm_classifier_gridsearch")

@register_strong_algorithm
class SmartTopNFrequentStrongNumber(SmartMainAlgorithmStrongAdapter):
    def __init__(self):
        super().__init__("top_n_frequent_per_position_v1")

@register_strong_algorithm
class SmartRecencyWeightedStrongNumber(SmartMainAlgorithmStrongAdapter):
    def __init__(self):
        super().__init__("recency_weighted_linear")

@register_strong_algorithm
class SmartLSTMStrongNumber(SmartMainAlgorithmStrongAdapter):
    def __init__(self):
        super().__init__("sequence_lstm_classifier_gridsearch")

