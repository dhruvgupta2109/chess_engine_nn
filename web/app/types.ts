export type GamePhase = "not_started" | "human_turn" | "engine_thinking" | "game_over";

export interface SearchInfo {
  depth: number;
  seldepth: number;
  score_cp: number | null;
  mate_in: number | null;
  nodes: number;
  nps: number;
  elapsed_ms: number;
  pv: string[];
  completed: boolean;
}

export interface GameState {
  game_number: number;
  generation: number;
  started: boolean;
  phase: GamePhase;
  fen: string;
  turn: "white" | "black";
  human_color: "white" | "black";
  engine_color: "white" | "black";
  think_time_ms: number;
  legal_moves: string[];
  moves: string[];
  captures: Record<"white" | "black", string[]>;
  material_advantage: Record<"white" | "black", number>;
  last_move: string | null;
  check_square: string | null;
  result: string | null;
  termination: string | null;
  search: SearchInfo | null;
}

export interface ServiceStatus {
  ok: boolean;
  api_version: number;
  model: {
    ready: boolean;
    name: string;
    sha256?: string;
  };
}

export interface GameEvent {
  type: string;
  payload: GameState | { message: string; state?: GameState };
}
