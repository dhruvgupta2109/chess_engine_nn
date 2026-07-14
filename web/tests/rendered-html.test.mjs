import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the Neural Chess product shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>Neural Chess<\/title>/i);
  assert.match(html, /Neural Chess/i);
  assert.match(html, /New Game/);
  assert.match(html, /Undo Turn/);
  assert.match(html, /Flip Board/);
  assert.match(html, /Resign/);
  assert.doesNotMatch(html, /codex-preview|SkeletonPreview|react-loading-skeleton/i);
});

test("keeps the Aurora design and local production bundle", async () => {
  const [css, board, game, panel, playerStrip, localIndex] = await Promise.all([
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/components/ChessBoard.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/components/ChessGame.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/components/GamePanel.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/components/PlayerStrip.tsx", import.meta.url), "utf8"),
    readFile(new URL("../../chess_engine_nn/web_api/static/index.html", import.meta.url), "utf8"),
  ]);

  assert.match(css, /--cyan:\s*#5ce6e6/i);
  assert.match(css, /backdrop-filter:\s*blur\(22px\)/i);
  assert.match(css, /prefers-reduced-motion:\s*reduce/i);
  assert.match(board, /role="grid"/);
  assert.match(board, /legal destination/);
  assert.match(game, /aria-live="polite"|role="alert"/);
  assert.doesNotMatch(game, /className="topbar"/);
  assert.match(panel, /panel-brand-row/);
  assert.match(playerStrip, /material-advantage/);
  assert.match(playerStrip, /captured-pieces/);
  assert.match(css, /overflow-y:\s*auto/);
  assert.match(localIndex, /Neural Chess/);
  await access(new URL("../../chess_engine_nn/web_api/static/assets", import.meta.url));
});
