from collections import Counter
from typing import List, Dict, Any
from models import Draw
from .base import StrongNumberAlgorithm, register_strong_algorithm

STRONG_NUMBER_REGISTRY = {}

def register_strong_algorithm(cls):
    STRONG_NUMBER_REGISTRY[cls.version] = cls
    return cls

@register_strong_algorithm
class MostCommonStrongNumber(StrongNumberAlgorithm):
    version = "most_common"
    description = "Pick the most common strong number from history."

    def predict(self, draws: List[Draw], numbers: List[int] = None, **kwargs) -> int:
        counter = Counter(draw.strong_number for draw in draws)
        if not counter:
            return 1  # fallback
        candidates = [num for num, _ in counter.most_common()]
        if numbers is not None:
            return self.pick_not_in(numbers, candidates)
        return candidates[0] 