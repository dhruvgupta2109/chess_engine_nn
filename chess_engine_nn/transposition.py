"""Bounded transposition table with alpha-beta bound semantics."""

from dataclasses import dataclass
from enum import StrEnum

import chess
import chess.polyglot


class BoundType(StrEnum):
    EXACT = "exact"
    LOWER = "lower"
    UPPER = "upper"


@dataclass(frozen=True)
class TranspositionEntry:
    key: int
    depth: int
    score: int
    bound: BoundType
    best_move: chess.Move | None
    generation: int


def position_hash(board: chess.Board) -> int:
    """Hash rule state used by search, including the fifty-move counter."""
    return chess.polyglot.zobrist_hash(board) ^ (board.halfmove_clock << 1)


class TranspositionTable:
    """Dictionary-backed bounded table with depth-preferred replacement."""

    ESTIMATED_ENTRY_BYTES = 128

    def __init__(self, size_mb: int = 64) -> None:
        if size_mb <= 0:
            raise ValueError("Transposition table size must be positive")
        self.size_mb = size_mb
        self.capacity = max(1, size_mb * 1024 * 1024 // self.ESTIMATED_ENTRY_BYTES)
        self._entries: dict[int, TranspositionEntry] = {}

    def __len__(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()

    def probe(self, key: int) -> TranspositionEntry | None:
        return self._entries.get(key)

    def store(self, entry: TranspositionEntry) -> None:
        existing = self._entries.get(entry.key)
        if existing is not None:
            if entry.depth >= existing.depth or entry.generation > existing.generation:
                self._entries[entry.key] = entry
            return
        if len(self._entries) >= self.capacity:
            victim_key = min(
                self._entries,
                key=lambda key: (
                    self._entries[key].generation,
                    self._entries[key].depth,
                ),
            )
            del self._entries[victim_key]
        self._entries[entry.key] = entry
