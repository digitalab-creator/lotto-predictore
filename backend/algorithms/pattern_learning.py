from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
from collections import Counter
import random
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class PatternLearningFromWinnersV1Algorithm(Algorithm):
    version = "pattern_learning_from_winners_v1"
    description = "Analyze winning lines with 4+ hits and extract common structural patterns. (v1)"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Step 1: Find all pairs of draws with 4+ hits
        winner_lines = []
        for i, draw1 in enumerate(draws):
            for j, draw2 in enumerate(draws):
                if i == j:
                    continue
                hits = len(set(draw1.numbers) & set(draw2.numbers))
                if hits >= 4:
                    winner_lines.append(sorted(draw1.numbers))
        if not winner_lines:
            winner_lines = [sorted(d.numbers) for d in draws[-num_for_analysis:]]
        # Step 2: Extract patterns
        delta_patterns = []
        parity_patterns = []
        digit_group_patterns = []
        for line in winner_lines:
            deltas = [line[i+1] - line[i] for i in range(5)]
            delta_patterns.append(tuple(deltas))
            parity = tuple(n % 2 for n in line)
            parity_patterns.append(parity)
            digit_groups = tuple(n // 10 for n in line)
            digit_group_patterns.append(digit_groups)
        # Most common patterns
        common_delta = Counter(delta_patterns).most_common(1)[0][0]
        common_parity = Counter(parity_patterns).most_common(1)[0][0]
        common_digit_group = Counter(digit_group_patterns).most_common(1)[0][0]
        # Step 3: Generate combos that match these patterns
        combos = []
        attempts = 0
        while len(combos) < num_for_analysis and attempts < 1000:
            # Start with a random base
            base = random.randint(1, 10)
            nums = [base]
            for d in common_delta:
                nums.append(nums[-1] + d)
            # Check parity and digit group
            if len(nums) == 6 and all(1 <= n <= 37 for n in nums):
                if tuple(n % 2 for n in nums) == common_parity and tuple(n // 10 for n in nums) == common_digit_group:
                    if len(set(nums)) == 6:
                        combos.append(nums)
            attempts += 1
        # Fallback: just use the most recent lines
        if not combos:
            combos = [sorted(d.numbers) for d in draws[-num_for_analysis:]]
        return [{"numbers": combo} for combo in combos[:num_to_recommend]] if combos else []

@register_algorithm
class PatternLearningFromWinnersV2Algorithm(Algorithm):
    version = "pattern_learning_from_winners_v2"
    description = "Analyze winning lines with 3+ hits and extract only delta patterns. (v2)"

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        # Step 1: Find all pairs of draws with 3+ hits
        winner_lines = []
        for i, draw1 in enumerate(draws):
            for j, draw2 in enumerate(draws):
                if i == j:
                    continue
                hits = len(set(draw1.numbers) & set(draw2.numbers))
                if hits >= 3:
                    winner_lines.append(sorted(draw1.numbers))
        if not winner_lines:
            winner_lines = [sorted(d.numbers) for d in draws[-num_for_analysis:]]
        # Step 2: Extract only delta patterns
        delta_patterns = []
        for line in winner_lines:
            deltas = [line[i+1] - line[i] for i in range(5)]
            delta_patterns.append(tuple(deltas))
        # Most common delta pattern
        common_delta = Counter(delta_patterns).most_common(1)[0][0]
        # Step 3: Generate combos that match this pattern
        combos = []
        attempts = 0
        while len(combos) < num_for_analysis and attempts < 1000:
            base = random.randint(1, 10)
            nums = [base]
            for d in common_delta:
                nums.append(nums[-1] + d)
            if len(nums) == 6 and all(1 <= n <= 37 for n in nums) and len(set(nums)) == 6:
                combos.append(nums)
            attempts += 1
        if not combos:
            combos = [sorted(d.numbers) for d in draws[-num_for_analysis:]]
        return [{"numbers": combo} for combo in combos[:num_to_recommend]] if combos else [] 