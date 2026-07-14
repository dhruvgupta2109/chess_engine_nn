"use client";

import type { GameState } from "../types";

const pieceGlyphs: Record<string, string> = {
  P: "♙",
  N: "♘",
  B: "♗",
  R: "♖",
  Q: "♕",
  p: "♟",
  n: "♞",
  b: "♝",
  r: "♜",
  q: "♛",
};

interface PlayerStripProps {
  state: GameState;
  color: "white" | "black";
}

export function PlayerStrip({ state, color }: PlayerStripProps) {
  const isHuman = state.human_color === color;
  const captured = state.captures[color];
  const advantage = state.material_advantage[color];
  const capturedLabel = captured.length
    ? `${captured.length} captured piece${captured.length === 1 ? "" : "s"}`
    : "No captured pieces";

  return (
    <div className="player-strip" aria-label={`${isHuman ? "You" : "Neural engine"}, ${color}`}>
      <div className="player-identity">
        <span className={`player-avatar ${isHuman ? "human" : "engine"}`} aria-hidden="true">
          {isHuman ? "Y" : "N"}
        </span>
        <span className="player-copy">
          <strong>{isHuman ? "You" : "Neural Engine"}</strong>
          <small>{color}</small>
        </span>
      </div>
      <div className="captured-material" aria-label={capturedLabel}>
        <span className="captured-pieces" aria-hidden="true">
          {captured.map((piece, index) => (
            <span className="captured-piece" key={`${piece}-${index}`}>{pieceGlyphs[piece]}</span>
          ))}
        </span>
        {advantage > 0 && <strong className="material-advantage">+{advantage}</strong>}
      </div>
    </div>
  );
}
