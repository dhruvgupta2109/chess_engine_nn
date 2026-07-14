"use client";

import { useCallback, useEffect, useState } from "react";
import { ChessBoard } from "./ChessBoard";
import { GamePanel } from "./GamePanel";
import { NewGameDialog } from "./NewGameDialog";
import { PlayerStrip } from "./PlayerStrip";
import { gameClient } from "../services/gameClient";
import type { GameEvent, GameState, ServiceStatus } from "../types";

const emptyState: GameState = {
  game_number: 0,
  generation: 0,
  started: false,
  phase: "not_started",
  fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  turn: "white",
  human_color: "white",
  engine_color: "black",
  think_time_ms: 1000,
  legal_moves: [],
  moves: [],
  captures: { white: [], black: [] },
  material_advantage: { white: 0, black: 0 },
  last_move: null,
  check_square: null,
  result: null,
  termination: null,
  search: null,
};

export function ChessGame() {
  const [state, setState] = useState<GameState>(emptyState);
  const [status, setStatus] = useState<ServiceStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newGameOpen, setNewGameOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [flipped, setFlipped] = useState(false);
  const [promotion, setPromotion] = useState<{ base: string; choices: string[] } | null>(null);
  const [confirmResign, setConfirmResign] = useState(false);
  const [reviewing, setReviewing] = useState(false);

  const connect = useCallback(async () => {
    setError(null);
    try {
      const [serviceStatus, current] = await Promise.all([gameClient.status(), gameClient.current()]);
      setStatus(serviceStatus);
      setState(current);
      setNewGameOpen(!current.started);
    } catch (connectionError) {
      setStatus(null);
      setError(connectionError instanceof Error ? connectionError.message : "Engine service unavailable");
    }
  }, []);

  useEffect(() => {
    const connectTimer = window.setTimeout(() => void connect(), 0);
    const socket = gameClient.events(
      (event: GameEvent) => {
        if (event.type === "error") {
          const payload = event.payload as { message: string; state?: GameState };
          setError(payload.message);
          if (payload.state) setState(payload.state);
          return;
        }
        setState(event.payload as GameState);
      },
      () => setError("Lost connection to the local engine service."),
    );
    return () => {
      window.clearTimeout(connectTimer);
      socket.close();
    };
  }, [connect]);

  async function runAction(action: () => Promise<GameState>): Promise<GameState | null> {
    setBusy(true);
    setError(null);
    try {
      const nextState = await action();
      setState(nextState);
      return nextState;
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Action failed");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function startGame(side: "white" | "black" | "random", thinkTime: number) {
    const nextState = await runAction(() => gameClient.newGame(side, thinkTime));
    if (!nextState) return;
    setNewGameOpen(false);
    setReviewing(false);
    setFlipped(nextState.human_color === "black");
  }

  function requestMove(base: string, choices: string[]) {
    if (choices.length) {
      setPromotion({ base, choices });
    } else {
      void runAction(() => gameClient.move(base));
    }
  }

  const gameOverVisible = state.phase === "game_over" && !reviewing;
  const bottomColor = flipped ? "black" : "white";
  const topColor = bottomColor === "white" ? "black" : "white";

  return (
    <main className="app-shell">
      {error && (
        <div className="error-banner" role="alert">
          {error} <button className="glass-button" onClick={() => void connect()}>Retry</button>
        </div>
      )}

      <div className="workspace">
        <section className="board-stage glass" aria-label="Game board">
          <div className="board-stack">
            <PlayerStrip state={state} color={topColor} />
            <ChessBoard state={state} flipped={flipped} onMove={requestMove} />
            <PlayerStrip state={state} color={bottomColor} />
          </div>
          {gameOverVisible && (
            <div className="game-over-card" role="dialog" aria-modal="true">
              <p className="eyebrow">Game complete</p>
              <h2>{state.result === "1/2-1/2" ? "Draw" : state.result === (state.human_color === "white" ? "1-0" : "0-1") ? "You won" : "Engine won"}</h2>
              <p>{state.termination?.replaceAll("_", " ")}</p>
              <div className="dialog-actions">
                <button className="glass-button" onClick={() => setReviewing(true)}>Review Board</button>
                <button className="glass-button primary" onClick={() => setNewGameOpen(true)}>Play Again</button>
              </div>
            </div>
          )}
        </section>
        <GamePanel
          state={state}
          serviceStatus={status}
          serviceError={error}
          onNewGame={() => setNewGameOpen(true)}
          onUndo={() => void runAction(gameClient.undo)}
          onFlip={() => setFlipped((value) => !value)}
          onResign={() => setConfirmResign(true)}
        />
      </div>

      <NewGameDialog open={newGameOpen} canClose={state.started} busy={busy} onClose={() => setNewGameOpen(false)} onStart={(side, time) => void startGame(side, time)} />

      {promotion && (
        <div className="dialog-backdrop">
          <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="promotion-title">
            <h2 id="promotion-title">Promote pawn</h2>
            <p>Choose the piece for your promotion.</p>
            <div className="promotion-grid">
              {promotion.choices.map((choice) => (
                <button className="promotion-piece" key={choice} aria-label={`Promote to ${choice}`} onClick={() => {
                  void runAction(() => gameClient.move(`${promotion.base}${choice}`));
                  setPromotion(null);
                }}>
                  {{ q: "♕", r: "♖", b: "♗", n: "♘" }[choice]}
                </button>
              ))}
            </div>
          </section>
        </div>
      )}

      {confirmResign && (
        <div className="dialog-backdrop">
          <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="resign-title">
            <h2 id="resign-title">Resign this game?</h2>
            <p>The current game will end immediately.</p>
            <div className="dialog-actions">
              <button className="glass-button" onClick={() => setConfirmResign(false)}>Keep Playing</button>
              <button className="glass-button danger" onClick={() => {
                setConfirmResign(false);
                void runAction(gameClient.resign);
              }}>Resign</button>
            </div>
          </section>
        </div>
      )}
    </main>
  );
}
