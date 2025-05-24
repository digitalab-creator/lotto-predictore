from collections import Counter
from typing import List, Dict, Any
from models import Draw
from .base import StrongNumberAlgorithm, register_strong_algorithm
from services.logger import dh_log

@register_strong_algorithm
class MostCommonStrongNumber(StrongNumberAlgorithm):
    version = "most_common"
    description = "Pick the most common strong number from history."

    def predict(self, draws: List[Draw], numbers: List[int] = None, **kwargs) -> int:
        dh_log(f"[most_common strong] Received {len(draws)} draws. First 3: {draws[:3]}", level="DEBUG")
        counter = Counter(draw.strong_number for draw in draws)
        dh_log(f"[most_common strong] Counter: {counter}", level="DEBUG")
        if not counter:
            dh_log("[most_common strong] Counter is empty, fallback to 1.", level="WARNING")
            strong_number = 1  # fallback
        else:
            candidates = [num for num, _ in counter.most_common()]
            dh_log(f"[most_common strong] Candidates: {candidates}", level="DEBUG")
            strong_number = candidates[0]
        self._validate_strong_number(strong_number)
        return strong_number 