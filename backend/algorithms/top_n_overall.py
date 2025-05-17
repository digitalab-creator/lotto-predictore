from collections import Counter
from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
import random
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class Top6OverallFrequentV1Algorithm(Algorithm):
    version = "top_6_overall_frequent_v1"
    description = "Top 6 most frequent numbers overall, generate combos. (v1)"

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
        # Generate combos by shuffling/rotating the top6
        combos = []
        for i in range(num_for_analysis):
            combo_numbers = top6[:]
            random.shuffle(combo_numbers)
            combos.append({"numbers": combo_numbers})
        # Return only the number to recommend
        return combos[:num_to_recommend] if combos else []

@register_algorithm
class Top6OverallFrequentV2Algorithm(Algorithm):
    version = "top_6_overall_frequent_v2"
    description = "Top 10 most frequent numbers overall, sample 6 for each combo. (v2)"

    def run(self, draws: List[Draw], top_n: int = 10, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        all_numbers = [n for draw in draws for n in draw.numbers]
        number_counts = Counter(all_numbers)
        top10 = [num for num, _ in number_counts.most_common(top_n)]
        if len(top10) < 6:
            return []
        combos = []
        for i in range(num_for_analysis):
            combo_numbers = random.sample(top10, 6)
            combos.append({"numbers": combo_numbers})
        return combos[:num_to_recommend] if combos else [] 