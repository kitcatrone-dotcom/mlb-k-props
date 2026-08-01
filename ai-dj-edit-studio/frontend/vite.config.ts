import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Electron loads the built app from a file:// origin, so asset URLs must be
// relative rather than absolute ("/assets/..." breaks under file://).
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: "dist",
  },
});
