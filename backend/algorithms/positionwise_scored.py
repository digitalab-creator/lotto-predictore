from collections import Counter
from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
import itertools
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class PositionwiseScoredV1Algorithm(Algorithm):
    version = "positionwise_scored_v1"
    description = "Top-N per position, score combos by frequency sum, pick top combos. (v1)"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Frequency by position
        position_counters = [Counter() for _ in range(6)]
        for draw in draws:
            for i, num in enumerate(draw.numbers):
                position_counters[i][num] += 1
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
        combos = []
        for combo in scored:
            combos.append({
                "numbers": list(combo),
                "params": {
                    "top_n": top_n,
                    "num_for_analysis": num_for_analysis,
                    "num_to_recommend": num_to_recommend,
                    "scoring": "sum"
                }
            })
        return combos[:num_to_recommend] if combos else []

@register_algorithm
class PositionwiseScoredV2Algorithm(Algorithm):
    version = "positionwise_scored_v2"
    description = "Top-N per position, score combos by weighted frequency (double for first/last position), pick top combos. (v2)"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        position_counters = [Counter() for _ in range(6)]
        for draw in draws:
            for i, num in enumerate(draw.numbers):
                position_counters[i][num] += 1
        top_numbers_per_pos = [
            [num for num, _ in counter.most_common(top_n)]
            for counter in position_counters
        ]
        combos = list(itertools.product(*top_numbers_per_pos))
        # Weighted score: double for first and last position
        def weighted_score(combo):
            weights = [2, 1, 1, 1, 1, 2]
            return sum(weights[i] * position_counters[i][num] for i, num in enumerate(combo))
        scored = sorted(combos, key=weighted_score, reverse=True)[:num_for_analysis]
        combos = []
        for combo in scored:
            combos.append({
                "numbers": list(combo),
                "params": {
                    "top_n": top_n,
                    "num_for_analysis": num_for_analysis,
                    "num_to_recommend": num_to_recommend,
                    "scoring": "weighted",
                    "weights": [2,1,1,1,1,2]
                }
            })
        return combos[:num_to_recommend] if combos else [] 