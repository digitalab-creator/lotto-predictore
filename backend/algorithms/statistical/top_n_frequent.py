from collections import Counter
from typing import List, Dict, Any
from models import Draw
from algorithms.base import Algorithm, register_algorithm
import itertools
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class TopNFrequentPerPositionV1Algorithm(Algorithm):
    version = "top_n_frequent_per_position_v1"
    description = "Top N frequent numbers per position, generate combos. (v1)"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Analyze frequency by position (1st-6th)
        position_counters = [Counter() for _ in range(6)]
        for draw in draws:
            for i, num in enumerate(draw.numbers):
                position_counters[i][num] += 1
        # Get top N frequent numbers per position
        top_numbers_per_pos = [
            [num for num, _ in counter.most_common(top_n)]
            for counter in position_counters
        ]
        # Generate all possible combinations (cartesian product)
        combos = list(itertools.product(*top_numbers_per_pos))
        # Limit to num_for_analysis combos for analysis
        combos = combos[:num_for_analysis]
        result = []
        for combo in combos[:num_to_recommend]:
            result.append({
                "numbers": list(combo),
                "params": {
                    "top_n": top_n,
                    "num_for_analysis": num_for_analysis,
                    "num_to_recommend": num_to_recommend
                }
            })
        return result if result else []

@register_algorithm
class TopNFrequentPerPositionV2Algorithm(Algorithm):
    version = "top_n_frequent_per_position_v2"
    description = "Top 5 frequent numbers per position, rotate strong number for each combo. (v2)"

    def run(self, draws: List[Draw], **kwargs) -> List[Dict]:
        """
        Run the Top N Frequent Per Position V2 algorithm.
        
        Args:
            draws: List of historical draws
            **kwargs: Additional parameters including:
                - top_n: Number of top frequent numbers per position (default: 3)
                - num_for_analysis: Number of draws to analyze (default: 8)
                - num_to_recommend: Number of combinations to recommend (default: 8)
        
        Returns:
            List of dictionaries with 'numbers' and 'params' keys
        """
        # Extract parameters
        top_n = kwargs.get('top_n', 3)
        num_for_analysis = kwargs.get('num_for_analysis', 8)
        num_to_recommend = kwargs.get('num_to_recommend', 8)
        
        # Use default values if not provided
        if num_for_analysis == 8 and num_to_recommend == 8:
            pass  # Use defaults
        
        # Get the most recent draws for analysis
        recent_draws = draws[-num_for_analysis:] if len(draws) >= num_for_analysis else draws
        
        # Create counters for each position
        position_counters = [Counter() for _ in range(6)]
        
        # Count frequency of each number in each position
        for draw in recent_draws:
            for pos, number in enumerate(draw.numbers):
                position_counters[pos][number] += 1
        
        # Get top N numbers for each position
        top_numbers_per_pos = []
        for pos in range(6):
            top_numbers = [num for num, _ in position_counters[pos].most_common(top_n)]
            top_numbers_per_pos.append(top_numbers)
        
        # Generate all possible combinations
        combinations = []
        for combo in itertools.product(*top_numbers_per_pos):
            combinations.append(combo)
        
        # Limit to requested number of recommendations
        combinations = combinations[:num_to_recommend]
        
        # Convert to result format
        results = []
        for combo in combinations:
            result = {
                'numbers': list(combo),
                'params': {
                    'top_n': top_n,
                    'num_for_analysis': num_for_analysis,
                    'num_to_recommend': num_to_recommend
                }
            }
            results.append(result)
        
        return results 