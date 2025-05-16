from collections import Counter
from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
import itertools
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class TopNFrequentAlgorithm(Algorithm):
    version = "v1"
    description = "Top N frequent numbers per position, generate combos."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Analyze frequency by position (1st-6th)
        position_counters = [Counter() for _ in range(6)]
        strong_counter = Counter()
        for draw in draws:
            for i, num in enumerate(draw.numbers):
                position_counters[i][num] += 1
            strong_counter[draw.strong_number] += 1
        # Get top N frequent numbers per position
        top_numbers_per_pos = [
            [num for num, _ in counter.most_common(top_n)]
            for counter in position_counters
        ]
        # Get top N strong numbers
        top_strongs = [num for num, _ in strong_counter.most_common(top_n)]
        # Generate all possible combinations (cartesian product)
        combos = list(itertools.product(*top_numbers_per_pos))
        # Limit to num_for_analysis combos for analysis
        combos = combos[:num_for_analysis]
        # Assign the most common strong number to all combos (could randomize or rotate if wanted)
        result = []
        for combo in combos[:num_to_recommend]:
            # Find a strong number not in the combo
            chosen_strong = None
            for s in top_strongs:
                if s not in combo:
                    chosen_strong = s
                    break
            if chosen_strong is None:
                # Debug log for FSM's glory
                print(f"[FSM DEBUG] All top strong numbers are in combo {combo}, using fallback 1!")
                chosen_strong = 1
            result.append({"numbers": list(combo), "strong": chosen_strong})
        return result if result else [] 