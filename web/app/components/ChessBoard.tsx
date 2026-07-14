"use client";

import { useMemo, useState } from "react";
import type { GameState } from "../types";

const pieces: Record<string, string> = {
  K: "♔",
  Q: "♕",
  R: "♖",
  B: "♗",
  N: "♘",
  P: "♙",
  k: "♚",
  q: "♛",
  r: "♜",
  b: "♝",
  n: "♞",
  p: "♟",
};

function parseFen(fen: string): Record<string, string> {
  const position: Record<string, string> = {};
  const rows = fen.split(" ")[0].split("/");
  rows.forEach((row, rowIndex) => {
    let file = 0;
    for (const token of row) {
      if (/\d/.test(token)) {
        file += Number(token);
      } else {
        position[`${String.fromCharCode(97 + file)}${8 - rowIndex}`] = token;
        file += 1;
      }
    }
  });
  return position;
}

interface ChessBoardProps {
  state: GameState;
  flipped: boolean;
  onMove: (move: string, promotions: string[]) => void;
}

export function ChessBoard({ state, flipped, onMove }: ChessBoardProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [dragSource, setDragSource] = useState<string | null>(null);
  const position = useMemo(() => parseFen(state.fen), [state.fen]);
  const files = flipped ? [..."hgfedcba"] : [..."abcdefgh"];
  const ranks = flipped ? [..."12345678"] : [..."87654321"];
  const sourceSquares = useMemo(
    () => new Set(state.legal_moves.map((move) => move.slice(0, 2))),
    [state.legal_moves],
  );
  const targets = useMemo(
    () =>
      new Set(
        selected
          ? state.legal_moves
              .filter((move) => move.startsWith(selected))
              .map((move) => move.slice(2, 4))
          : [],
      ),
    [selected, state.legal_moves],
  );
  const lastSquares = new Set(
    state.last_move ? [state.last_move.slice(0, 2), state.last_move.slice(2, 4)] : [],
  );

  function tryMove(from: string, to: string) {
    const candidates = state.legal_moves.filter((move) => move.startsWith(`${from}${to}`));
    if (!candidates.length) {
      setSelected(sourceSquares.has(to) ? to : null);
      return;
    }
    const promotions = candidates.map((move) => move.slice(4)).filter(Boolean);
    setSelected(null);
    onMove(`${from}${to}`, promotions);
  }

  function activate(square: string) {
    if (state.phase !== "human_turn") return;
    if (selected) {
      tryMove(selected, square);
    } else if (sourceSquares.has(square)) {
      setSelected(square);
    }
  }

  return (
    <div className="board-wrap">
      <div className="board" role="grid" aria-label="Chessboard">
        {ranks.flatMap((rank, rankIndex) =>
          files.map((file, fileIndex) => {
            const square = `${file}${rank}`;
            const piece = position[square];
            const isTarget = targets.has(square);
            const interactive = state.phase === "human_turn" && (sourceSquares.has(square) || isTarget);
            const classes = [
              "square",
              (file.charCodeAt(0) - 97 + Number(rank)) % 2 === 0 ? "light" : "dark",
              interactive ? "interactive" : "",
              selected === square ? "selected" : "",
              lastSquares.has(square) ? "last" : "",
              state.check_square === square ? "in-check" : "",
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <button
                className={classes}
                key={square}
                role="gridcell"
                aria-label={`${square}${piece ? `, ${piece === piece.toUpperCase() ? "white" : "black"} piece` : ""}${isTarget ? ", legal destination" : ""}`}
                onClick={() => activate(square)}
                onDragOver={(event) => isTarget && event.preventDefault()}
                onDrop={() => {
                  if (dragSource) tryMove(dragSource, square);
                  setDragSource(null);
                }}
              >
                {rankIndex === 7 && <span className="coordinate file">{file}</span>}
                {fileIndex === 0 && <span className="coordinate rank">{rank}</span>}
                {isTarget && (piece ? <span className="target-ring" /> : <span className="target-dot" />)}
                {piece && (
                  <span
                    className={`piece ${piece === piece.toUpperCase() ? "white" : "black"}`}
                    draggable={sourceSquares.has(square) && state.phase === "human_turn"}
                    onDragStart={() => {
                      setDragSource(square);
                      setSelected(square);
                    }}
                    onDragEnd={() => setDragSource(null)}
                  >
                    {pieces[piece]}
                  </span>
                )}
              </button>
            );
          }),
        )}
      </div>
    </div>
  );
}
