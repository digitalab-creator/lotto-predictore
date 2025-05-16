from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
from collections import Counter
import random
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class SkipDistanceFrequencyAlgorithm(Algorithm):
    version = "v10"
    description = "Select numbers that haven't appeared in the longest time (most 'due' numbers)."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Track the last seen date for each number
        last_seen = {}
        for draw in draws:
            for num in draw.numbers:
                last_seen[num] = draw.date
        # Sort numbers by oldest last seen date (i.e., most 'due')
        sorted_by_gap = sorted(last_seen.items(), key=lambda x: x[1])[:6]
        due_numbers = [num for num, _ in sorted_by_gap]
        if len(due_numbers) < 6:
            return []
        # Most common strong number
        strong_counter = Counter(draw.strong_number for draw in draws)
        top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
        # Generate combos by shuffling the due numbers
        combos = []
        for _ in range(num_for_analysis):
            combo_numbers = due_numbers[:]
            random.shuffle(combo_numbers)
            combos.append({"numbers": combo_numbers, "strong": top_strong})
        return combos[:num_to_recommend] if combos else []
 