"""Iterative-deepening neural negamax search."""

from collections.abc import Callable
from dataclasses import dataclass
import threading
import time

import chess

from chess_engine_nn.evaluator import PositionEvaluator
from chess_engine_nn.time_control import SearchLimits, allocated_time_ms
from chess_engine_nn.transposition import (
    BoundType,
    TranspositionEntry,
    TranspositionTable,
    position_hash,
)

MATE_SCORE = 32_000
MATE_THRESHOLD = 31_000
INFINITY = 40_000


class SearchStopped(Exception):
    """Internal cooperative-cancellation signal."""


@dataclass(frozen=True)
class SearchResult:
    best_move: chess.Move | None
    score_cp: int | None
    mate_in: int | None
    depth: int
    seldepth: int
    nodes: int
    elapsed_ms: int
    principal_variation: tuple[chess.Move, ...]
    completed: bool
    nps: int
    transposition_hits: int


SearchObserver = Callable[[SearchResult], None]


def mate_distance(score: int) -> int | None:
    if abs(score) < MATE_THRESHOLD:
        return None
    plies = MATE_SCORE - abs(score)
    moves = (plies + 1) // 2
    return moves if score > 0 else -moves


def score_to_transposition(score: int, ply: int) -> int:
    """Remove root-relative ply from mate scores before table storage."""
    if score >= MATE_THRESHOLD:
        return score + ply
    if score <= -MATE_THRESHOLD:
        return score - ply
    return score


def score_from_transposition(score: int, ply: int) -> int:
    """Restore root-relative mate distance after a table probe."""
    if score >= MATE_THRESHOLD:
        return score - ply
    if score <= -MATE_THRESHOLD:
        return score + ply
    return score


class SearchEngine:
    """Single-threaded iterative search over legal ``python-chess`` moves."""

    def __init__(
        self,
        evaluator: PositionEvaluator,
        *,
        hash_mb: int = 64,
        max_quiescence_depth: int = 8,
        aspiration_window_cp: int = 50,
    ) -> None:
        if max_quiescence_depth < 0 or aspiration_window_cp <= 0:
            raise ValueError("Search depth/window configuration is invalid")
        self.evaluator = evaluator
        self.table = TranspositionTable(hash_mb)
        self.max_quiescence_depth = max_quiescence_depth
        self.aspiration_window_cp = aspiration_window_cp
        self.generation = 0
        self.killers: dict[int, list[chess.Move]] = {}
        self.history: dict[tuple[bool, int, int], int] = {}
        self._reset_search_state()

    def _reset_search_state(self) -> None:
        self.nodes = 0
        self.seldepth = 0
        self.transposition_hits = 0
        self.deadline: float | None = None
        self.node_limit: int | None = None
        self.stop_event: threading.Event | None = None
        self.started = 0.0

    def search(
        self,
        board: chess.Board,
        limits: SearchLimits,
        observer: SearchObserver | None = None,
        stop_event: threading.Event | None = None,
    ) -> SearchResult:
        """Search a copy of ``board`` and return the last completed iteration."""
        limits.validate()
        self._reset_search_state()
        self.generation += 1
        self.started = time.monotonic()
        self.node_limit = limits.nodes
        self.stop_event = stop_event
        budget = allocated_time_ms(limits, white_to_move=board.turn == chess.WHITE)
        if budget is not None:
            self.deadline = self.started + budget / 1000
        position = board.copy(stack=True)
        terminal = self._terminal_score(position, 0)
        if terminal is not None:
            return self._result(None, terminal, 0, (), True)

        legal_moves = list(position.legal_moves)
        fallback = self._ordered_moves(position, legal_moves, None, 0)[0]
        completed_result: SearchResult | None = None
        previous_score = 0
        maximum_depth = limits.depth or 64
        for depth in range(1, maximum_depth + 1):
            try:
                if depth == 1 or completed_result is None:
                    alpha, beta = -INFINITY, INFINITY
                else:
                    alpha = previous_score - self.aspiration_window_cp
                    beta = previous_score + self.aspiration_window_cp
                score, pv = self._negamax(position, depth, alpha, beta, 0)
                if score <= alpha or score >= beta:
                    score, pv = self._negamax(position, depth, -INFINITY, INFINITY, 0)
                if not pv:
                    pv = (fallback,)
                previous_score = score
                completed_result = self._result(pv[0], score, depth, pv, True)
                if observer is not None:
                    observer(completed_result)
                if abs(score) >= MATE_THRESHOLD:
                    break
            except SearchStopped:
                break

        if completed_result is not None:
            if self._should_stop() and completed_result.depth < maximum_depth:
                return self._result(
                    completed_result.best_move,
                    completed_result.score_cp or 0,
                    completed_result.depth,
                    completed_result.principal_variation,
                    False,
                )
            return completed_result
        return self._result(fallback, None, 0, (fallback,), False)

    def _result(
        self,
        move: chess.Move | None,
        score: int | None,
        depth: int,
        pv: tuple[chess.Move, ...],
        completed: bool,
    ) -> SearchResult:
        elapsed_ms = max(0, int((time.monotonic() - self.started) * 1000))
        nps = int(self.nodes * 1000 / max(1, elapsed_ms))
        return SearchResult(
            best_move=move,
            score_cp=score if score is None or abs(score) < MATE_THRESHOLD else None,
            mate_in=mate_distance(score) if score is not None else None,
            depth=depth,
            seldepth=self.seldepth,
            nodes=self.nodes,
            elapsed_ms=elapsed_ms,
            principal_variation=pv,
            completed=completed,
            nps=nps,
            transposition_hits=self.transposition_hits,
        )

    def _check_stop(self) -> None:
        if self.node_limit is not None and self.nodes >= self.node_limit:
            raise SearchStopped
        if self.stop_event is not None and self.stop_event.is_set():
            raise SearchStopped
        if self.deadline is not None and time.monotonic() >= self.deadline:
            raise SearchStopped

    def _should_stop(self) -> bool:
        return (
            (self.node_limit is not None and self.nodes >= self.node_limit)
            or (self.stop_event is not None and self.stop_event.is_set())
            or (self.deadline is not None and time.monotonic() >= self.deadline)
        )

    def _terminal_score(self, board: chess.Board, ply: int) -> int | None:
        if board.is_checkmate():
            return -MATE_SCORE + ply
        if (
            board.is_stalemate()
            or board.is_insufficient_material()
            or board.is_fifty_moves()
            or board.can_claim_fifty_moves()
            or board.is_repetition(3)
            or board.can_claim_threefold_repetition()
        ):
            return 0
        return None

    def _negamax(
        self, board: chess.Board, depth: int, alpha: int, beta: int, ply: int
    ) -> tuple[int, tuple[chess.Move, ...]]:
        self._check_stop()
        self.nodes += 1
        self.seldepth = max(self.seldepth, ply)
        terminal = self._terminal_score(board, ply)
        if terminal is not None:
            return terminal, ()
        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply, 0), ()

        original_alpha = alpha
        key = position_hash(board)
        entry = None if board.is_repetition(2) or board.halfmove_clock >= 90 else self.table.probe(key)
        if entry is not None and entry.depth >= depth:
            self.transposition_hits += 1
            entry_score = score_from_transposition(entry.score, ply)
            if entry.bound == BoundType.EXACT:
                return entry_score, (entry.best_move,) if entry.best_move else ()
            if entry.bound == BoundType.LOWER:
                alpha = max(alpha, entry_score)
            else:
                beta = min(beta, entry_score)
            if alpha >= beta:
                return entry_score, (entry.best_move,) if entry.best_move else ()

        best_score = -INFINITY
        best_move: chess.Move | None = None
        best_pv: tuple[chess.Move, ...] = ()
        moves = self._ordered_moves(board, list(board.legal_moves), entry.best_move if entry else None, ply)
        for move in moves:
            is_quiet = not board.is_capture(move) and move.promotion is None
            board.push(move)
            try:
                child_score, child_pv = self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
                score = -child_score
            finally:
                board.pop()
            if score > best_score:
                best_score = score
                best_move = move
                best_pv = (move, *child_pv)
            alpha = max(alpha, score)
            if alpha >= beta:
                if is_quiet:
                    self._record_killer(move, ply)
                    history_key = (board.turn, move.from_square, move.to_square)
                    self.history[history_key] = self.history.get(history_key, 0) + depth * depth
                break

        bound = (
            BoundType.UPPER
            if best_score <= original_alpha
            else BoundType.LOWER
            if best_score >= beta
            else BoundType.EXACT
        )
        if not (board.is_repetition(2) or board.halfmove_clock >= 90):
            self.table.store(
                TranspositionEntry(
                    key,
                    depth,
                    score_to_transposition(best_score, ply),
                    bound,
                    best_move,
                    self.generation,
                )
            )
        return best_score, best_pv

    def _quiescence(
        self, board: chess.Board, alpha: int, beta: int, ply: int, qdepth: int
    ) -> int:
        self._check_stop()
        self.nodes += 1
        self.seldepth = max(self.seldepth, ply)
        terminal = self._terminal_score(board, ply)
        if terminal is not None:
            return terminal

        in_check = board.is_check()
        if not in_check:
            stand_pat = int(self.evaluator.evaluate(board))
            stand_pat = max(-MATE_THRESHOLD + 1, min(MATE_THRESHOLD - 1, stand_pat))
            if stand_pat >= beta:
                return stand_pat
            alpha = max(alpha, stand_pat)
        if qdepth >= self.max_quiescence_depth:
            if not in_check:
                return alpha
            score = int(self.evaluator.evaluate(board))
            return max(-MATE_THRESHOLD + 1, min(MATE_THRESHOLD - 1, score))

        moves = list(board.legal_moves) if in_check else [
            move for move in board.legal_moves if board.is_capture(move) or move.promotion is not None
        ]
        moves = self._ordered_moves(board, moves, None, ply)
        for move in moves:
            board.push(move)
            try:
                score = -self._quiescence(board, -beta, -alpha, ply + 1, qdepth + 1)
            finally:
                board.pop()
            if score >= beta:
                return score
            alpha = max(alpha, score)
        return alpha

    def _record_killer(self, move: chess.Move, ply: int) -> None:
        killers = self.killers.setdefault(ply, [])
        if move in killers:
            killers.remove(move)
        killers.insert(0, move)
        del killers[2:]

    def _ordered_moves(
        self,
        board: chess.Board,
        moves: list[chess.Move],
        table_move: chess.Move | None,
        ply: int,
    ) -> list[chess.Move]:
        piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20_000,
        }

        def score(move: chess.Move) -> int:
            if move == table_move:
                return 10_000_000
            value = 0
            if move.promotion:
                value += 1_000_000 + piece_values[move.promotion]
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                if victim is None and board.is_en_passant(move):
                    victim_value = piece_values[chess.PAWN]
                else:
                    victim_value = piece_values[victim.piece_type] if victim else 0
                attacker = board.piece_at(move.from_square)
                attacker_value = piece_values[attacker.piece_type] if attacker else 0
                value += 500_000 + 10 * victim_value - attacker_value
            if move in self.killers.get(ply, ()):
                value += 100_000 - self.killers[ply].index(move)
            value += self.history.get((board.turn, move.from_square, move.to_square), 0)
            return value

        return sorted(moves, key=lambda move: (-score(move), move.uci()))
