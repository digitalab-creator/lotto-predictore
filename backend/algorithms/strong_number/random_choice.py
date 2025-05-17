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
            return 1
        if numbers is not None:
            return self.pick_not_in(numbers, strongs)
        return random.choice(strongs) 