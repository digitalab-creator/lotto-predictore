from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
from collections import Counter
import random
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class RepeatedPatternMatchingAlgorithm(Algorithm):
    version = "v5"
    description = "Find historical lines with 4+ hits and reuse/alter them."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Find all historical lines that matched 4+ numbers in any draw
        candidate_lines = set()
        for i, draw1 in enumerate(draws):
            for j, draw2 in enumerate(draws):
                if i == j:
                    continue
                hits = len(set(draw1.numbers) & set(draw2.numbers))
                if hits >= 4:
                    candidate_lines.add(tuple(sorted(draw1.numbers)))
        # If not enough, just use the most recent draws
        candidate_lines = list(candidate_lines)
        if len(candidate_lines) < num_for_analysis:
            candidate_lines += [tuple(sorted(d.numbers)) for d in draws[-num_for_analysis:]]
        # Slightly alter some lines (swap a number or change one)
        combos = []
        for line in candidate_lines[:num_for_analysis]:
            nums = list(line)
            if random.random() < 0.5:
                # Swap two numbers
                a, b = random.sample(range(6), 2)
                nums[a], nums[b] = nums[b], nums[a]
            else:
                # Change one number
                idx = random.randint(0, 5)
                nums[idx] = random.randint(1, 37)
            # Ensure unique and sorted
            nums = sorted(set(nums))
            if len(nums) == 6:
                combos.append(nums)
        # Pick the most common strong number
        strong_counter = Counter(draw.strong_number for draw in draws)
        top_strong = strong_counter.most_common(1)[0][0] if strong_counter else 1
        return [{"numbers": combo, "strong": top_strong} for combo in combos[:num_to_recommend]] if combos else [] 