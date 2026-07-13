"""Typed application errors used at package boundaries."""


class ChessEngineError(Exception):
    """Base class for expected engine failures."""


class ConfigurationError(ChessEngineError):
    """Raised when configuration is missing, unknown, or invalid."""


class EncodingError(ChessEngineError):
    """Raised when a chess position cannot be encoded safely."""


class ModelArtifactError(ChessEngineError):
    """Raised when a model artifact is corrupt or incompatible."""
