import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import { fileURLToPath } from "node:url";

const dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(dirname, "src") },
  },
  server: {
    proxy: {
      // Desenvolvimento local: /api → backend FastAPI (uvicorn :8000)
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: {
    // code splitting: bibliotecas 3D de mapas virarão chunks lazy (fase de mapas)
    rollupOptions: {},
  },
});
