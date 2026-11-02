import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Built into ../web, which is committed: the Pi serves it at home (it has no Node to build with),
// and the rockridge-lights Worker serves it on the internet. `npm run dev` talks to the real Pi.
const PI = "http://192.168.0.7:8080";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: { outDir: "../web", emptyOutDir: true, chunkSizeWarningLimit: 1500 },
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: { proxy: { "/api": PI, "/sounds": PI } },
});
