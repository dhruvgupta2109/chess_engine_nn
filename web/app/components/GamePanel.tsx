"use client";

import type { GameState, ServiceStatus } from "../types";

interface GamePanelProps {
  state: GameState;
  serviceStatus: ServiceStatus | null;
  serviceError: string | null;
  onNewGame: () => void;
  onUndo: () => void;
  onFlip: () => void;
  onResign: () => void;
}

function statusCopy(state: GameState): [string, string, string] {
  if (state.phase === "engine_thinking") return ["Engine move", "Engine thinking", "Searching the position"];
  if (state.phase === "game_over") return ["Game complete", state.result ?? "Game over", state.termination?.replaceAll("_", " ") ?? ""];
  if (state.phase === "human_turn") return ["Your move", "Your turn", `Playing as ${state.human_color}`];
  return ["Ready", "Start a game", "Choose your side and think time"];
}

export function GamePanel({
  state,
  serviceStatus,
  serviceError,
  onNewGame,
  onUndo,
  onFlip,
  onResign,
}: GamePanelProps) {
  const [eyebrow, title, detail] = statusCopy(state);
  const search = state.search;
  const canUndo = state.moves.length >= (state.human_color === "white" ? 1 : 2);
  const rows = Array.from({ length: Math.ceil(state.moves.length / 2) }, (_, index) => ({
    number: index + 1,
    white: state.moves[index * 2],
    black: state.moves[index * 2 + 1],
  }));
  return (
    <aside className="side-panel glass" aria-label="Game information">
      <div className="panel-brand-row">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true" />
          <div className="brand-copy"><strong>Neural Chess</strong><span>CPU-first intelligence</span></div>
        </div>
        <div
          className={`model-status ${serviceStatus ? "" : "offline"}`}
          title={serviceStatus?.model.sha256 ?? serviceError ?? undefined}
        >
          <span className="status-dot" />
          <span>{serviceStatus ? "Model ready" : "Engine offline"}</span>
        </div>
      </div>
      <p className="sr-only" aria-live="polite">{eyebrow}. {title}. {detail}</p>

      <div className="stats" aria-label="Engine search statistics">
        <div className="stat"><span>Depth</span><strong>{search?.depth ?? "—"}</strong></div>
        <div className="stat"><span>Nodes</span><strong>{search ? search.nodes.toLocaleString() : "—"}</strong></div>
        <div className="stat"><span>Time</span><strong>{search ? `${(search.elapsed_ms / 1000).toFixed(1)}s` : "—"}</strong></div>
      </div>

      <section className="history-card">
        <h2>Move history</h2>
        {rows.length ? (
          <ol className="move-list">
            {rows.map((row) => (
              <li className="move-row" key={row.number}>
                <span className="move-number">{String(row.number).padStart(2, "0")}</span>
                <span>{row.white}</span>
                <span>{row.black ?? ""}</span>
              </li>
            ))}
          </ol>
        ) : (
          <div className="empty-history">Your moves will appear here.</div>
        )}
      </section>

      <div className="controls">
        <button className="glass-button primary" onClick={onNewGame}>New Game</button>
        <button className="glass-button" onClick={onUndo} disabled={!canUndo}>Undo Turn</button>
        <button className="glass-button" onClick={onFlip}>Flip Board</button>
        <button className="glass-button danger" onClick={onResign} disabled={!state.started || state.phase === "game_over"}>Resign</button>
      </div>
    </aside>
  );
}
