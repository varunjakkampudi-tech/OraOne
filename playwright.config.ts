import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end test configuration.
 *
 * The suites expect the full local stack to be running: the API on port 8000
 * and the web app on E2E_BASE_URL (default http://localhost:5180). See the
 * "Testing" section of README.md.
 *
 * Suites are selected with tags in the test titles:
 *   @smoke      fast check that the main pages render
 *   @sanity     every Product 1 route responds and renders
 *   @critical   sign-in, workspace and session flows that must never break
 *   @regression navigation, menus and interactions
 *   @visual     screenshot comparison of key layouts
 */
const baseURL = process.env["E2E_BASE_URL"] ?? "http://localhost:5180";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  // Each test may compile routes on the development server, so allow two minutes.
  timeout: 120_000,
  forbidOnly: Boolean(process.env["CI"]),
  retries: process.env["CI"] ? 2 : 0,
  // Two workers keep the development server responsive across browsers.
  workers: 2,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  outputDir: "test-results",
  expect: {
    // The dev server compiles each route on first visit, so allow time to render.
    timeout: 15_000,
    // Visual comparisons tolerate sub-pixel anti-aliasing differences only.
    toHaveScreenshot: { maxDiffPixelRatio: 0.01, animations: "disabled" },
  },
  use: {
    baseURL,
    // The dev server compiles routes on demand, so the first visit can be slow.
    navigationTimeout: 90_000,
    actionTimeout: 20_000,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
    { name: "mobile-chrome", use: { ...devices["Pixel 7"] } },
    { name: "mobile-safari", use: { ...devices["iPhone 14"] } },
  ],
});
