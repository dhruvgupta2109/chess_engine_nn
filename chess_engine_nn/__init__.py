"""CPU-first neural chess engine foundations."""

from chess_engine_nn.encoding import FEATURE_COUNT, FEATURE_SCHEMA_VERSION, FeatureEncoder
from chess_engine_nn.evaluator import MaterialEvaluator, PositionEvaluator, load_evaluator
from chess_engine_nn.search import SearchEngine, SearchResult
from chess_engine_nn.time_control import SearchLimits

__all__ = [
    "FEATURE_COUNT",
    "FEATURE_SCHEMA_VERSION",
    "FeatureEncoder",
    "MaterialEvaluator",
    "PositionEvaluator",
    "SearchEngine",
    "SearchLimits",
    "SearchResult",
    "load_evaluator",
]

__version__ = "0.1.0"
