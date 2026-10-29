import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

/**
 * M16 — Counselor, on its reserved port 5216 (PORTS.txt).
 *
 * This repo holds one module, so this is the app. Platform_Shell mounts the
 * same `src/routes.tsx`, so what you fix here is what students get.
 */
const API_TARGET = process.env.VITE_API_BASE ?? "http://127.0.0.1:8116";
/** M11, the voice engine (PORTS.txt 8111): the counselor's voice and face. */
const VOICE_TARGET = process.env.VITE_VOICE_BASE ?? "http://127.0.0.1:8111";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  optimizeDeps: {
    exclude: ["@ai/core"],
    include: ["@myned-ai/gsplat-flame-avatar-renderer"],
  },
  server: {
    port: 5216,
    strictPort: true,
    proxy: {
      "/v1/voice": { target: VOICE_TARGET, changeOrigin: true },
      "/v1": { target: API_TARGET, changeOrigin: true },
      "/health": { target: API_TARGET, changeOrigin: true },
    },
  },
  preview: { port: 5216, strictPort: true },
});
