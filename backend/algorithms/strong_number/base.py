from typing import List, Any
import random

class StrongNumberAlgorithm:
    version = "base"
    description = "Base class for strong number algorithms. Override predict()."

    def predict(self, draws: List[Any], **kwargs) -> int:
        raise NotImplementedError

    @staticmethod
    def pick_not_in(numbers: List[int], candidates: List[int]) -> int:
        """
        Pick a strong number from candidates that is not in numbers. If all are in, pick random 1-7 not in numbers, else fallback to 1.
        """
        options = [s for s in candidates if s not in numbers]
        if options:
            return random.choice(options)
        all_options = [s for s in range(1, 8) if s not in numbers]
        if all_options:
            return random.choice(all_options)
        return 1

STRONG_NUMBER_REGISTRY = {}

def register_strong_algorithm(cls):
    STRONG_NUMBER_REGISTRY[cls.version] = cls
    return cls 