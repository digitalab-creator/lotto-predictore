from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
from collections import Counter
import random
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class BalancedSpreadAlgorithm(Algorithm):
    version = "v8"
    description = "Balanced spread: 4 fixed ranges, pick 2 from each, sample 6."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        ranges = [range(1, 11), range(11, 21), range(21, 31), range(31, 38)]
        combos = []
        for _ in range(num_for_analysis):
            pool = []
            for r in ranges:
                pool.extend(random.sample(list(r), 2))
            combo_numbers = random.sample(pool, 6)
            combos.append(combo_numbers)
        strong_counter = Counter(draw.strong_number for draw in draws)
        top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
        return [{"numbers": combo, "strong": top_strong} for combo in combos[:num_to_recommend]] if combos else []

@register_algorithm
class BalancedSpreadEqualAlgorithm(Algorithm):
    version = "v8-equal"
    description = "Balanced spread: 6 equal ranges, pick 1 from each."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # 6 equal ranges (1-6, 7-12, ..., 31-36, 37)
        ranges = [range(1, 7), range(7, 13), range(13, 19), range(19, 25), range(25, 31), range(31, 38)]
        combos = []
        for _ in range(num_for_analysis):
            combo_numbers = [random.choice(list(r)) for r in ranges]
            combos.append(combo_numbers)
        strong_counter = Counter(draw.strong_number for draw in draws)
        top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
        return [{"numbers": combo, "strong": top_strong} for combo in combos[:num_to_recommend]] if combos else []

@register_algorithm
class BalancedSpreadRandomAlgorithm(Algorithm):
    version = "v8-random"
    description = "Balanced spread: 6 random ranges of size 6, pick 1 from each."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        all_numbers = list(range(1, 38))
        combos = []
        for _ in range(num_for_analysis):
            random.shuffle(all_numbers)
            ranges = [all_numbers[i*6:(i+1)*6] for i in range(6)]
            combo_numbers = [random.choice(r) for r in ranges if r]
            combos.append(combo_numbers)
        strong_counter = Counter(draw.strong_number for draw in draws)
        top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
        return [{"numbers": combo, "strong": top_strong} for combo in combos[:num_to_recommend]] if combos else [] 