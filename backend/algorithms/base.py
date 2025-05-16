from typing import List, Dict, Any

# Base class for all algorithms
class Algorithm:
    version = "base"
    description = "Base algorithm class. Override run()."

    def run(self, draws: List[Any], top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Given a list of Draw objects, return 8 combinations as list of dicts:
        [{"numbers": [...], "strong": ...}, ...]
        """
        raise NotImplementedError

# Registry for all algorithm versions
ALGORITHM_REGISTRY = {}

def register_algorithm(cls):
    ALGORITHM_REGISTRY[cls.version] = cls
    return cls 