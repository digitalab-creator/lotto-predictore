from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
from collections import Counter
import random
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class RandomFromTopPoolAlgorithm(Algorithm):
    version = "random_from_top15_pool"
    description = "Pick 6 numbers randomly from top 15 frequent numbers."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Flatten all numbers from all draws
        all_numbers = [n for draw in draws for n in draw.numbers]
        pool = [n for n, _ in Counter(all_numbers).most_common(15)]
        if len(pool) < 6:
            return []
        combos = []
        for _ in range(num_for_analysis):
            combo_numbers = random.sample(pool, 6)
            combos.append({
                "numbers": combo_numbers,
                "params": {
                    "top_n": top_n,
                    "num_for_analysis": num_for_analysis,
                    "num_to_recommend": num_to_recommend
                }
            })
        return combos[:num_to_recommend] if combos else []

@register_algorithm
class RandomFromTop10PoolAlgorithm(Algorithm):
    version = "random_from_top10_pool"
    description = "Pick 6 numbers randomly from top 10 frequent numbers."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        all_numbers = [n for draw in draws for n in draw.numbers]
        pool = [n for n, _ in Counter(all_numbers).most_common(10)]
        if len(pool) < 6:
            return []
        combos = []
        for _ in range(num_for_analysis):
            combo_numbers = random.sample(pool, 6)
            combos.append({
                "numbers": combo_numbers,
                "params": {
                    "top_n": top_n,
                    "num_for_analysis": num_for_analysis,
                    "num_to_recommend": num_to_recommend
                }
            })
        return combos[:num_to_recommend] if combos else []

@register_algorithm
class RandomFromTop20PoolAlgorithm(Algorithm):
    version = "random_from_top20_pool"
    description = "Pick 6 numbers randomly from top 20 frequent numbers."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        all_numbers = [n for draw in draws for n in draw.numbers]
        pool = [n for n, _ in Counter(all_numbers).most_common(20)]
        if len(pool) < 6:
            return []
        combos = []
        for _ in range(num_for_analysis):
            combo_numbers = random.sample(pool, 6)
            combos.append({
                "numbers": combo_numbers,
                "params": {
                    "top_n": top_n,
                    "num_for_analysis": num_for_analysis,
                    "num_to_recommend": num_to_recommend
                }
            })
        return combos[:num_to_recommend] if combos else [] 