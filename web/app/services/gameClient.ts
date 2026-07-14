import type { GameEvent, GameState, ServiceStatus } from "../types";

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8765";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const gameClient = {
  status: () => request<ServiceStatus>("/api/v1/status"),
  current: () => request<GameState>("/api/v1/games/current"),
  newGame: (humanSide: "white" | "black" | "random", thinkTimeMs: number) =>
    request<GameState>("/api/v1/games", {
      method: "POST",
      body: JSON.stringify({ human_side: humanSide, think_time_ms: thinkTimeMs }),
    }),
  move: (move: string) =>
    request<GameState>("/api/v1/games/current/moves", {
      method: "POST",
      body: JSON.stringify({ move }),
    }),
  undo: () => request<GameState>("/api/v1/games/current/undo", { method: "POST" }),
  resign: () => request<GameState>("/api/v1/games/current/resign", { method: "POST" }),
  events(onEvent: (event: GameEvent) => void, onDisconnect: () => void): WebSocket {
    const socketBase = apiBase.replace(/^http/, "ws");
    const socket = new WebSocket(`${socketBase}/api/v1/events`);
    socket.onmessage = (message) => onEvent(JSON.parse(message.data) as GameEvent);
    socket.onclose = onDisconnect;
    socket.onerror = onDisconnect;
    return socket;
  },
};
