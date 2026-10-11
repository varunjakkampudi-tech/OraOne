const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: true,
  reporter: [["list"], ["html", { outputFolder: "output/playwright/report", open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3001",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    ...devices["Desktop Chrome"],
  },
  webServer: {
    command: "npm start",
    url: "http://127.0.0.1:3001",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      PORT: "3001",
      REACT_APP_API_URL: "",
      REACT_APP_AUTH_PROVIDER: "cognito",
      REACT_APP_COGNITO_DOMAIN: "https://ap-southeast-2cfhugatzr.auth.ap-southeast-2.amazoncognito.com",
      REACT_APP_COGNITO_CLIENT_ID: "6nr1n019eiihlh89vpmu31p1im",
      REACT_APP_COGNITO_REDIRECT_URI: "http://127.0.0.1:3001/auth/callback",
    },
  },
});
