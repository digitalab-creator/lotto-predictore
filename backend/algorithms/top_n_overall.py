from collections import Counter
from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
import random
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class TopNOverallFrequencyAlgorithm(Algorithm):
    version = "v2"
    description = "Top 6 most frequent numbers overall, generate combos."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Flatten all numbers from all draws
        all_numbers = [n for draw in draws for n in draw.numbers]
        number_counts = Counter(all_numbers)
        # Get the 6 most common numbers
        top6 = [num for num, _ in number_counts.most_common(6)]
        if len(top6) < 6:
            # Not enough data, fallback
            return []
        # Get the most common strong number
        strong_counter = Counter(draw.strong_number for draw in draws)
        top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
        # Generate combos by shuffling/rotating the top6
        combos = []
        for i in range(num_for_analysis):
            combo_numbers = top6[:]
            random.shuffle(combo_numbers)
            combos.append({"numbers": combo_numbers, "strong": top_strong})
        # Return only the number to recommend
        return combos[:num_to_recommend] if combos else [] 