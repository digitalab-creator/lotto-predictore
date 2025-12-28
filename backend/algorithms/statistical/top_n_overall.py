from collections import Counter
from typing import List, Dict, Any
from models import Draw
from algorithms.base import Algorithm, register_algorithm
import random
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND
from logger import logger

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
            combos.append({
                "numbers": combo_numbers,
                "params": {
                    "top_n": 6,
                    "num_for_analysis": num_for_analysis,
                    "num_to_recommend": num_to_recommend
                }
            })
        # Return only the number to recommend
        return combos[:num_to_recommend] if combos else []

@register_algorithm
class Top6OverallFrequentV2Algorithm(Algorithm):
    version = "top_6_overall_frequent_v2"
    description = "Top 10 most frequent numbers overall, sample 6 for each combo. (v2)"

    def run(self, draws: List[Draw], top_n: int = 10, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        logger.debug(f"[top_6_overall_frequent_v2] Total draws received: {len(draws)}")
        if draws:
            logger.debug(f"[top_6_overall_frequent_v2] Type of first draw: {type(draws[0])}")
        for idx, draw in enumerate(draws[:10]):
            logger.info(f"[top_6_overall_frequent_v2] Draw {idx} numbers type: {type(getattr(draw, 'numbers', None))}, value: {getattr(draw, 'numbers', None)}", context=None)
            if not hasattr(draw, 'numbers') or draw.numbers is None or not isinstance(draw.numbers, (list, tuple)) or not all(isinstance(n, int) for n in draw.numbers):
                logger.warning(f"[top_6_overall_frequent_v2] WARNING: Draw {idx} numbers is not a list/tuple of ints: {getattr(draw, 'numbers', None)}", context=None)
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        if not draws:
            logger.error(f"[top_6_overall_frequent_v2] ERROR: No draws provided!", context=None)
            raise ValueError("No draws provided to top_6_overall_frequent_v2")
        for idx, draw in enumerate(draws):
            if not hasattr(draw, 'numbers') or draw.numbers is None or not isinstance(draw.numbers, (list, tuple)):
                logger.error(f"[top_6_overall_frequent_v2] ERROR: Draw at index {idx} has invalid numbers: {getattr(draw, 'numbers', None)}", context=None)
                raise ValueError(f"Draw at index {idx} has invalid numbers: {getattr(draw, 'numbers', None)}")
        all_numbers = [n for draw in draws for n in draw.numbers]
        unique_numbers = set(all_numbers)
        logger.info(f"[top_6_overall_frequent_v2] First 10 draws' numbers: {[draw.numbers for draw in draws[:10]]}", context=None)
        logger.info(f"[top_6_overall_frequent_v2] Unique numbers in all draws: {sorted(unique_numbers)} (count: {len(unique_numbers)})", context=None)
        number_counts = Counter(all_numbers)
        logger.info(f"[top_6_overall_frequent_v2] Full number frequency Counter: {number_counts}", context=None)
        logger.info(f"[top_6_overall_frequent_v2] top_n param: {top_n}", context=None)
        if top_n < 6:
            logger.error(f"[top_6_overall_frequent_v2] ERROR: top_n={top_n} is too small, must be at least 6!", context=None)
            raise ValueError("top_n must be at least 6 for top_6_overall_frequent_v2")
        top10 = [num for num, _ in number_counts.most_common(top_n)]
        logger.info(f"[top_6_overall_frequent_v2] Top10 numbers: {top10}", context=None)
        if len(top10) < 6:
            logger.error(f"[top_6_overall_frequent_v2] Not enough numbers in top10: {top10} (draws: {len(draws)})", context=None)
            return []
        combos = []
        for i in range(num_for_analysis):
            combo_numbers = random.sample(top10, 6)
            combos.append({
                "numbers": combo_numbers,
                "params": {
                    "top_n": top_n,
                    "num_for_analysis": num_for_analysis,
                    "num_to_recommend": num_to_recommend
                }
            })
        logger.info(f"[top_6_overall_frequent_v2] Generated {len(combos)} combos. First 3: {combos[:3]}", context=None)
        return combos[:num_to_recommend] if combos else [] 