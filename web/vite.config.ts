/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "./" makes every asset URL relative, so the same build works at any path:
// https://<user>.github.io/<repo>/, a subdirectory of another site, or a local file server.
// The app fetches its data relative to index.html ("data/manifest.json"), not from "/".
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: { outDir: "dist", sourcemap: true },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    restoreMocks: true,
  },
});
