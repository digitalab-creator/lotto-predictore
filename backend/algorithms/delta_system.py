import random
from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
from collections import Counter
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class DeltaSystemDataDrivenAlgorithm(Algorithm):
    version = "v4-data"
    description = "Delta system: use most common delta (gap) patterns from historical draws."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Analyze historical draws to find the most common delta patterns
        delta_patterns = []
        for draw in draws:
            sorted_nums = sorted(draw.numbers)
            deltas = [sorted_nums[i+1] - sorted_nums[i] for i in range(5)]
            delta_patterns.append(tuple(deltas))
        pattern_counter = Counter(delta_patterns)
        # Get the N most common patterns
        most_common_patterns = [list(pattern) for pattern, _ in pattern_counter.most_common(num_for_analysis)]
        combos = []
        for deltas in most_common_patterns:
            base = random.randint(1, 5)
            numbers = [base]
            for d in deltas:
                numbers.append(numbers[-1] + d)
            numbers = [n for n in numbers if 1 <= n <= 37]
            if len(numbers) == 6 and len(set(numbers)) == 6:
                combos.append(numbers)
        strong_counter = Counter(draw.strong_number for draw in draws)
        top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
        return [{"numbers": combo, "strong": top_strong} for combo in combos[:num_to_recommend]] if combos else []

@register_algorithm
class DeltaSystemFixedAlgorithm(Algorithm):
    version = "v4-fixed"
    description = "Delta system: use classic fixed delta (gap) patterns."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Classic fixed delta patterns
        deltas_list = [
            [3, 5, 6, 4, 2],   # Example: larger gaps at the start, smaller at the end
            [2, 4, 5, 3, 2],   # Example: moderate gaps, then smaller
            [1, 3, 4, 6, 2],   # Example: small start, big middle, small end
            [2, 3, 5, 4, 1],   # Example: moderate, then small
            [1, 2, 3, 4, 5],   # Example: strictly increasing gaps
            [2, 2, 2, 2, 2],   # Example: all gaps the same (even spacing)
            [1, 4, 4, 4, 2],   # Example: big gaps in the middle
            [3, 3, 3, 3, 3],   # Example: all gaps the same (medium spacing)
        ]
        combos = []
        for deltas in deltas_list[:num_for_analysis]:
            base = random.randint(1, 5)
            numbers = [base]
            for d in deltas:
                numbers.append(numbers[-1] + d)
            numbers = [n for n in numbers if 1 <= n <= 37]
            if len(numbers) == 6 and len(set(numbers)) == 6:
                combos.append(numbers)
        strong_counter = Counter(draw.strong_number for draw in draws)
        top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
        return [{"numbers": combo, "strong": top_strong} for combo in combos[:num_to_recommend]] if combos else [] 