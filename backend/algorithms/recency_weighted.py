from typing import List, Dict, Any
from models import Draw
from .base import Algorithm, register_algorithm
from collections import Counter
from datetime import datetime, timedelta
import random
from config import NUM_COMBINATIONS_FOR_ANALYSIS, NUM_COMBINATIONS_TO_RECOMMEND

@register_algorithm
class RecencyWeightedFrequencyAlgorithm(Algorithm):
    version = "recency_weighted_linear"
    description = "Weigh recent draws more heavily in frequency calculation (linear)."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, **kwargs) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        as_of_date = kwargs.get("as_of_date")
        if as_of_date is None:
            raise ValueError("as_of_date is required for recency-weighted algorithms")
        rng = kwargs.get("rng") or random
        # Linear recency weight: 1 / (days_ago + 1)
        counter = Counter()
        for draw in draws:
            days_ago = (as_of_date - draw.date).days
            weight = 1 / (days_ago + 1)
            for n in draw.numbers:
                counter[n] += weight
        top6 = [num for num, _ in counter.most_common(6)]
        if len(top6) < 6:
            return []
        combos = []
        for _ in range(num_for_analysis):
            combo_numbers = top6[:]
            rng.shuffle(combo_numbers)
            combos.append({
                "numbers": combo_numbers,
                "params": {
                    "top_n": top_n,
                    "num_for_analysis": num_for_analysis,
                    "num_to_recommend": num_to_recommend,
                    "weighting": "linear"
                }
            })
        return combos[:num_to_recommend] if combos else []

@register_algorithm
class RecencyWeightedExpAlgorithm(Algorithm):
    version = "recency_weighted_exponential"
    description = "Weigh recent draws more heavily using exponential decay."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, **kwargs) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        as_of_date = kwargs.get("as_of_date")
        if as_of_date is None:
            raise ValueError("as_of_date is required for recency-weighted algorithms")
        rng = kwargs.get("rng") or random
        # Exponential decay: weight = exp(-lambda * days_ago)
        import math
        counter = Counter()
        decay_lambda = 0.01  # Tune as needed
        for draw in draws:
            days_ago = (as_of_date - draw.date).days
            weight = math.exp(-decay_lambda * days_ago)
            for n in draw.numbers:
                counter[n] += weight
        top6 = [num for num, _ in counter.most_common(6)]
        if len(top6) < 6:
            return []
        combos = []
        for _ in range(num_for_analysis):
            combo_numbers = top6[:]
            rng.shuffle(combo_numbers)
            combos.append({
                "numbers": combo_numbers,
                "params": {
                    "top_n": top_n,
                    "num_for_analysis": num_for_analysis,
                    "num_to_recommend": num_to_recommend,
                    "weighting": "exponential",
                    "decay_lambda": decay_lambda
                }
            })
        return combos[:num_to_recommend] if combos else []

@register_algorithm
class RecencyWeightedWindowAlgorithm(Algorithm):
    version = "recency_weighted_window"
    description = "Only use draws from the last 1 year."

    def run(self, draws: List[Draw], top_n: int = 3, num_for_analysis: int = None, num_to_recommend: int = None, **kwargs) -> List[Dict[str, Any]]:
        if num_for_analysis is None:
            num_for_analysis = NUM_COMBINATIONS_FOR_ANALYSIS
        if num_to_recommend is None:
            num_to_recommend = NUM_COMBINATIONS_TO_RECOMMEND
        as_of_date = kwargs.get("as_of_date")
        if as_of_date is None:
            raise ValueError("as_of_date is required for recency-weighted algorithms")
        rng = kwargs.get("rng") or random
        one_year_ago = as_of_date - timedelta(days=365)
        recent_draws = [d for d in draws if d.date >= one_year_ago]
        counter = Counter()
        for draw in recent_draws:
            for n in draw.numbers:
                counter[n] += 1
        top6 = [num for num, _ in counter.most_common(6)]
        if len(top6) < 6:
            return []
        combos = []
        window_days = 365
        for _ in range(num_for_analysis):
            combo_numbers = top6[:]
            rng.shuffle(combo_numbers)
            combos.append({
                "numbers": combo_numbers,
                "params": {
                    "top_n": top_n,
                    "num_for_analysis": num_for_analysis,
                    "num_to_recommend": num_to_recommend,
                    "weighting": "window",
                    "window_days": window_days
                }
            })
        return combos[:num_to_recommend] if combos else [] 