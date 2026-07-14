"use client";

import { useState } from "react";

interface NewGameDialogProps {
  open: boolean;
  canClose: boolean;
  busy: boolean;
  onClose: () => void;
  onStart: (side: "white" | "black" | "random", thinkTime: number) => void;
}

export function NewGameDialog({ open, canClose, busy, onClose, onStart }: NewGameDialogProps) {
  const [side, setSide] = useState<"white" | "black" | "random">("white");
  const [thinkTime, setThinkTime] = useState(1000);
  if (!open) return null;
  return (
    <div className="dialog-backdrop" role="presentation">
      <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="new-game-title">
        <h2 id="new-game-title">New game</h2>
        <p>Choose your side and how long the neural engine may think for each move.</p>
        <fieldset className="choice-group">
          <legend>Your side</legend>
          <div className="choice-grid">
            {(["white", "black", "random"] as const).map((choice) => (
              <button key={choice} className={`choice-button ${side === choice ? "active" : ""}`} onClick={() => setSide(choice)}>
                {choice[0].toUpperCase() + choice.slice(1)}
              </button>
            ))}
          </div>
        </fieldset>
        <fieldset className="choice-group">
          <legend>Engine think time</legend>
          <div className="choice-grid">
            {[
              [250, "Fast"],
              [1000, "Normal"],
              [3000, "Strong"],
            ].map(([milliseconds, label]) => (
              <button key={milliseconds} className={`choice-button ${thinkTime === milliseconds ? "active" : ""}`} onClick={() => setThinkTime(milliseconds as number)}>
                {label}
              </button>
            ))}
          </div>
        </fieldset>
        <div className="dialog-actions">
          {canClose && <button className="glass-button" onClick={onClose}>Cancel</button>}
          <button className="glass-button primary" disabled={busy} onClick={() => onStart(side, thinkTime)}>
            {busy ? "Starting…" : "Start Game"}
          </button>
        </div>
      </section>
    </div>
  );
}
