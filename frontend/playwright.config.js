const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: [
    ["list"],
    ["html", { outputFolder: "output/playwright/report", open: "never" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:3002",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    ...devices["Desktop Chrome"],
  },
  webServer: {
    command: "npm start",
    url: "http://127.0.0.1:3002",
    // E2E exercises local email/password/OTP UI. Never reuse the developer's
    // app server, which may be configured differently or have an active session.
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      PORT: "3002",
      REACT_APP_API_URL: "",
      REACT_APP_AUTH_PROVIDER: "self_hosted",
    },
  },
});
