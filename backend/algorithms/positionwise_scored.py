from collections import Counter
from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
import itertools
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class PositionwiseScoredAlgorithm(Algorithm):
    version = "v3"
    description = "Top-N per position, score combos by frequency sum, pick top combos."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Frequency by position
        position_counters = [Counter() for _ in range(6)]
        strong_counter = Counter()
        for draw in draws:
            for i, num in enumerate(draw.numbers):
                position_counters[i][num] += 1
            strong_counter[draw.strong_number] += 1
        # Top N per position
        top_numbers_per_pos = [
            [num for num, _ in counter.most_common(top_n)]
            for counter in position_counters
        ]
        # All possible combos
        combos = list(itertools.product(*top_numbers_per_pos))
        # Score combos
        def score(combo):
            return sum(position_counters[i][num] for i, num in enumerate(combo))
        scored = sorted(combos, key=score, reverse=True)[:num_for_analysis]
        # Most common strong
        top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
        return [{"numbers": list(combo), "strong": top_strong} for combo in scored[:num_to_recommend]] if scored else [] 