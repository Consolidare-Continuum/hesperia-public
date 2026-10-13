import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base so the built `dist/` can be served from any URL path (nginx subdir or static host).
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
