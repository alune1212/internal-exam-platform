import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    // Keep the deterministic frontend gate within the stable worker budget.
    maxWorkers: 4,
    setupFiles: ["./src/test/setup.ts"],
  },
});
