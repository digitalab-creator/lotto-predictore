from collections import Counter
from typing import List, Dict, Any
from models import Draw
from .base import StrongNumberAlgorithm, register_strong_algorithm
from logger import logger

@register_strong_algorithm
class MostCommonStrongNumber(StrongNumberAlgorithm):
    version = "most_common"
    description = "Pick the most common strong number from history."

    def predict(self, draws: List[Draw], numbers: List[int] = None, **kwargs) -> int:
        logger.debug(f"[most_common strong] Received {len(draws)} draws. First 3: {draws[:3]}")
        counter = Counter(draw.strong_number for draw in draws)
        logger.info(f"[most_common strong] Counter: {counter}")
        if not counter:
            logger.warning("[most_common strong] Counter is empty, fallback to 1.")
            strong_number = 1  # fallback
        else:
            candidates = [num for num, _ in counter.most_common()]
            logger.info(f"[most_common strong] Candidates: {candidates}")
            strong_number = candidates[0]
        self._validate_strong_number(strong_number)
        return strong_number 