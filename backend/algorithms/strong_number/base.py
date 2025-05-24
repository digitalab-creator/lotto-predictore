from typing import List, Any
import random

class StrongNumberAlgorithm:
    version = "base"
    description = "Base class for strong number algorithms. Override predict()."

    def predict(self, draws: List[Any], **kwargs) -> int:
        raise NotImplementedError

    def _validate_strong_number(self, strong_number: int):
        if not (1 <= strong_number <= 7):
            raise ValueError(f"Invalid strong number: {strong_number}")

STRONG_NUMBER_REGISTRY = {}

def register_strong_algorithm(cls):
    STRONG_NUMBER_REGISTRY[cls.version] = cls
    return cls 