import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// Bundles mcp-app.html and its script into one self-contained HTML file under dist/,
// which the server returns as the ui:// resource for the Demo Setup card.
export default defineConfig({
  plugins: [viteSingleFile()],
  build: {
    outDir: "dist",
    emptyOutDir: false,
    rollupOptions: { input: process.env.INPUT ?? "mcp-app.html" },
  },
});
