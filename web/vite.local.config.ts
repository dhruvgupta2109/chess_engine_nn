import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  root: "local",
  plugins: [react()],
  define: {
    "process.env.NEXT_PUBLIC_API_BASE": "undefined",
  },
  build: {
    outDir: "../../chess_engine_nn/web_api/static",
    emptyOutDir: true,
  },
});
