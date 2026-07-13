"""CPU-first neural chess engine foundations."""

from chess_engine_nn.encoding import FEATURE_COUNT, FEATURE_SCHEMA_VERSION, FeatureEncoder
from chess_engine_nn.evaluator import MaterialEvaluator, PositionEvaluator

__all__ = [
    "FEATURE_COUNT",
    "FEATURE_SCHEMA_VERSION",
    "FeatureEncoder",
    "MaterialEvaluator",
    "PositionEvaluator",
]

__version__ = "0.1.0"
