import { defineConfig, devices } from "@playwright/test";

const outputDir = process.env.PLAYWRIGHT_OUTPUT_DIR ?? "test-results/playwright";
const reportDir = process.env.PLAYWRIGHT_REPORT_DIR ?? "playwright-report";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI
    ? [["line"], ["html", { open: "never", outputFolder: reportDir }]]
    : "list",
  timeout: 90_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.E2E_CANDIDATE_URL ?? "http://127.0.0.1:18080",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium-desktop",
      use: {
        ...devices["Desktop Chrome"],
        ...(process.env.E2E_BROWSER_CHANNEL ? { channel: process.env.E2E_BROWSER_CHANNEL } : {}),
      },
    },
  ],
  outputDir,
});
