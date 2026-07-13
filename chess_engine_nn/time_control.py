"""Search limits and CPU-safe move-time allocation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchLimits:
    depth: int | None = None
    nodes: int | None = None
    move_time_ms: int | None = None
    white_time_ms: int | None = None
    black_time_ms: int | None = None
    white_increment_ms: int = 0
    black_increment_ms: int = 0
    moves_to_go: int | None = None

    def validate(self) -> None:
        direct = (self.depth, self.nodes, self.move_time_ms)
        if any(value is not None and value <= 0 for value in direct):
            raise ValueError("Depth, nodes, and move time must be positive")
        clocks = (self.white_time_ms, self.black_time_ms)
        if any(value is not None and value < 0 for value in clocks):
            raise ValueError("Clock values cannot be negative")
        if self.white_increment_ms < 0 or self.black_increment_ms < 0:
            raise ValueError("Clock increments cannot be negative")
        if self.moves_to_go is not None and self.moves_to_go <= 0:
            raise ValueError("moves_to_go must be positive")


def allocated_time_ms(limits: SearchLimits, *, white_to_move: bool) -> int | None:
    """Return a conservative move budget, or None when search is not timed."""
    limits.validate()
    if limits.move_time_ms is not None:
        return limits.move_time_ms
    remaining = limits.white_time_ms if white_to_move else limits.black_time_ms
    increment = limits.white_increment_ms if white_to_move else limits.black_increment_ms
    if remaining is None:
        return None
    if remaining == 0:
        return 1
    moves = limits.moves_to_go or 30
    budget = remaining / moves + increment * 0.8
    safety = max(10, min(100, remaining // 20))
    return max(1, min(int(budget), max(1, remaining - safety)))
