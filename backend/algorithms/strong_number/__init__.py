# Arrr, strong number algorithms live here! Import all for registry.
from .base import STRONG_NUMBER_REGISTRY, register_strong_algorithm
from .most_common import *
from .recency_weighted import *
from .random_choice import *
# Import the new main algorithm adapters and hybrid algorithms
from .main_algorithm_adapters import *
from .hybrid_strong import * 