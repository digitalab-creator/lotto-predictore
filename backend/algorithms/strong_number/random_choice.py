import random
from typing import List, Dict, Any
from models import Draw
from .base import StrongNumberAlgorithm, register_strong_algorithm

@register_strong_algorithm
class RandomStrongNumber(StrongNumberAlgorithm):
    version = "random"
    description = "Pick a random strong number from those seen in history."

    def predict(self, draws: List[Draw], numbers: List[int] = None, **kwargs) -> int:
        strongs = list(set(draw.strong_number for draw in draws))
        if not strongs:
            strong_number = 1
        else:
            strong_number = random.choice(strongs)
        self._validate_strong_number(strong_number)
        return strong_number 