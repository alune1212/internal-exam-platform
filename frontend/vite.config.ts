import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return undefined;
          }
          if (id.includes("react-router-dom") || id.includes("@remix-run")) {
            return "router-vendor";
          }
          if (id.includes("@tanstack/react-query")) {
            return "query-vendor";
          }
          if (id.includes("@tanstack/react-table")) {
            return "table-vendor";
          }
          if (id.includes("@radix-ui") || id.includes("class-variance-authority")) {
            return "ui-vendor";
          }
          if (id.includes("lucide-react")) {
            return "icons-vendor";
          }
          if (id.includes("react") || id.includes("react-dom")) {
            return "react-vendor";
          }
          return undefined;
        },
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
