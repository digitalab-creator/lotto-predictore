from collections import Counter
from typing import List, Dict, Any
from models import Draw
from datetime import datetime
from .base import StrongNumberAlgorithm, register_strong_algorithm

@register_strong_algorithm
class RecencyWeightedStrongNumber(StrongNumberAlgorithm):
    version = "recency_weighted"
    description = "Weigh recent draws more heavily for strong number prediction."

    def predict(self, draws: List[Draw], numbers: List[int] = None, **kwargs) -> int:
        now = datetime.now().date()
        counter = Counter()
        for draw in draws:
            days_ago = (now - draw.date).days
            weight = 1 / (days_ago + 1)
            counter[draw.strong_number] += weight
        if not counter:
            strong_number = 1
        else:
            candidates = [num for num, _ in counter.most_common()]
            strong_number = candidates[0]
        self._validate_strong_number(strong_number)
        return strong_number 