import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = env.BACKEND_URL || "localhost:8000";
  return {
    plugins: [react()],
    server: {
      port: Number(process.env.PORT) || Number(env.FRONTEND_PORT) || 5173,
      proxy: {
        "/api": { target: `http://${backend}`, changeOrigin: true },
        "/ws": { target: `ws://${backend}`, ws: true },
      },
    },
  };
});
