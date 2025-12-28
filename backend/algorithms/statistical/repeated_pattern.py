from typing import List, Dict, Any
from models import Draw
from algorithms.base import Algorithm, register_algorithm
import random
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class RepeatedPatternMatchingV1Algorithm(Algorithm):
    version = "repeated_pattern_matching_v1"
    description = "Find historical lines with 4+ hits and reuse/alter them. (v1)"

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
                combos.append({
                    "numbers": nums,
                    "params": {
                        "top_n": top_n,
                        "num_for_analysis": num_for_analysis,
                        "num_to_recommend": num_to_recommend
                    }
                })
        return combos[:num_to_recommend] if combos else []

@register_algorithm
class RepeatedPatternMatchingV2Algorithm(Algorithm):
    version = "repeated_pattern_matching_v2"
    description = "Find historical lines with 3+ hits and always swap two numbers for alteration. (v2)"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Find all historical lines that matched 3+ numbers in any draw
        candidate_lines = set()
        for i, draw1 in enumerate(draws):
            for j, draw2 in enumerate(draws):
                if i == j:
                    continue
                hits = len(set(draw1.numbers) & set(draw2.numbers))
                if hits >= 3:
                    candidate_lines.add(tuple(sorted(draw1.numbers)))
        candidate_lines = list(candidate_lines)
        if len(candidate_lines) < num_for_analysis:
            candidate_lines += [tuple(sorted(d.numbers)) for d in draws[-num_for_analysis:]]
        combos = []
        for line in candidate_lines[:num_for_analysis]:
            nums = list(line)
            # Always swap two numbers
            a, b = random.sample(range(6), 2)
            nums[a], nums[b] = nums[b], nums[a]
            nums = sorted(set(nums))
            if len(nums) == 6:
                combos.append({
                    "numbers": nums,
                    "params": {
                        "top_n": top_n,
                        "num_for_analysis": num_for_analysis,
                        "num_to_recommend": num_to_recommend
                    }
                })
        return combos[:num_to_recommend] if combos else [] 