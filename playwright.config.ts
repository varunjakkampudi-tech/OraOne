import { defineConfig } from "@playwright/test";

/**
 * Browser tests for the product surfaces at phone, tablet and desktop widths.
 *
 * The default run uses the Vite dev server on E2E_BASE_URL (default
 * http://localhost:5173). If a server is already running there it is reused;
 * otherwise `npm run dev` is started for the run. Studio and install tests mock
 * every /api request in the browser (see e2e/product-support.ts), so no backend
 * is needed.
 *
 * Only the suites listed in `testMatch` run by default. The older suites in
 * e2e/ need a live API and are not part of this run.
 */
const baseURL = process.env["E2E_BASE_URL"] ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  testMatch: [
    "public-site.spec.ts",
    "studio.spec.ts",
    "channel-setup.spec.ts",
    "admin.spec.ts",
    "install.spec.ts",
    "auth.spec.ts",
  ],
  fullyParallel: true,
  // The dev server compiles each route on first visit, so allow generous time.
  timeout: 90_000,
  forbidOnly: Boolean(process.env["CI"]),
  retries: 0,
  workers: 2,
  reporter: [["list"]],
  outputDir: "test-results",
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL,
    navigationTimeout: 60_000,
    actionTimeout: 15_000,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "390",
      use: { browserName: "chromium", viewport: { width: 390, height: 844 } },
    },
    {
      name: "768",
      use: { browserName: "chromium", viewport: { width: 768, height: 1024 } },
    },
    {
      name: "1280",
      use: { browserName: "chromium", viewport: { width: 1280, height: 800 } },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: baseURL,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
