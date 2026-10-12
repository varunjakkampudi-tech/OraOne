const { test, expect } = require("@playwright/test");

const cognitoDomain =
  "https://ap-southeast-2cfhugatzr.auth.ap-southeast-2.amazoncognito.com";

async function mockUnauthenticatedApi(page) {
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      status: 401,
      body: JSON.stringify({ detail: "Not authenticated." }),
    }),
  );
  await page.route("**/api/auth/identity", (route) =>
    route.fulfill({
      status: 401,
      body: JSON.stringify({ detail: "Not authenticated." }),
    }),
  );
}

async function mockCognitoPage(page) {
  await page.route(`${cognitoDomain}/**`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "text/html",
      body: "<!doctype html><title>Mock Cognito</title><main>Mock Cognito managed login</main>",
    }),
  );
}

test.describe("email-only Cognito entry points", () => {
  test.beforeEach(async ({ page }) => {
    await mockUnauthenticatedApi(page);
    await mockCognitoPage(page);
  });

  test("signup opens Cognito registration, not a login-only form", async ({
    page,
  }) => {
    await page.goto("/signup");
    await page
      .getByRole("button", { name: "Continue with email" })
      .click();
    await expect.poll(() => page.url()).toContain(`${cognitoDomain}/signup?`);
    expect(await page.url()).toContain("scope=openid+email+profile");
    expect(await page.url()).not.toContain("phone");
  });

  test("login uses PKCE and binds the callback to state", async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto("/login");
    await page.getByRole("button", { name: "Continue with email" }).click();
    await expect.poll(() => page.url()).toContain("code_challenge_method=S256");
    const authorizeUrl = await page.url();
    const transaction = {
      state: new URL(authorizeUrl).searchParams.get("state"),
    };
    expect(transaction.state).toBeTruthy();
    await page.goto("http://127.0.0.1:3001/login");
    expect(
      await page.evaluate(() =>
        sessionStorage.getItem("oraone_cognito_pkce_verifier"),
      ),
    ).toBeTruthy();
    expect(
      await page.evaluate(() =>
        sessionStorage.getItem("oraone_cognito_oauth_state"),
      ),
    ).toBe(transaction.state);

    await page.goto(
      `http://127.0.0.1:3001/auth/callback?code=replay-code&state=wrong-state`,
    );
    await expect(
      page.getByRole("link", { name: "Return to login" }),
    ).toBeVisible();
    expect(
      await page.evaluate(() =>
        sessionStorage.getItem("oraone_cognito_pkce_verifier"),
      ),
    ).toBeNull();
    expect(
      await page.evaluate(() =>
        sessionStorage.getItem("oraone_cognito_oauth_state"),
      ),
    ).toBeNull();
  });

  test("forgot password opens Cognito's managed recovery endpoint without a redirect loop", async ({
    page,
  }) => {
    await page.goto("/forgot-password");
    await page
      .getByRole("button", { name: "Continue with email" })
      .click();
    await expect
      .poll(() => page.url())
      .toContain(`${cognitoDomain}/forgotPassword?`);
  });

  test("protected API access and logout use the browser session", async ({
    page,
  }) => {
    let logoutCalled = false;
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          userId: "user-1",
          email: "user@example.com",
          name: "Test User",
          role: "owner",
          plan: "free",
          status: "active",
          createdAt: new Date().toISOString(),
          lastLogin: new Date().toISOString(),
        }),
      }),
    );
    await page.route("**/api/auth/identity", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user: {
            id: "user-1",
            cognito_sub: "sub-1",
            email: "user@example.com",
            full_name: "Test User",
            avatar_url: null,
            role: "owner",
            status: "active",
            created_at: new Date().toISOString(),
            last_login_at: new Date().toISOString(),
          },
          organization: {
            id: "org-1",
            name: "Test Workspace",
            slug: "test-workspace",
            plan: "free",
            owner_user_id: "user-1",
            created_at: new Date().toISOString(),
          },
          membership: {
            id: "membership-1",
            organization_id: "org-1",
            user_id: "user-1",
            role: "owner",
            status: "active",
            joined_at: new Date().toISOString(),
          },
          is_new_user: false,
        }),
      }),
    );
    await page.route("**/api/auth/cognito/logout", (route) => {
      logoutCalled = true;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ message: "Logged out." }),
      });
    });
    await page.goto("/app/dashboard");
    await page.getByRole("button", { name: "Open profile menu" }).click();
    await page.getByTestId("profile-logout").click();
    await expect(page).toHaveURL(/\/login$/);
    expect(logoutCalled).toBe(true);
  });

  test("unified product portfolio presents all products with honest availability", async ({
    page,
  }) => {
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          userId: "user-1",
          email: "user@example.com",
          name: "Test User",
          role: "owner",
          plan: "free",
          status: "active",
        }),
      }),
    );
    await page.route("**/api/auth/identity", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user: {
            id: "user-1",
            email: "user@example.com",
            full_name: "Test User",
            role: "owner",
            status: "active",
          },
          organization: { id: "org-1", name: "Test Workspace", plan: "free" },
          membership: { role: "owner", status: "active" },
          is_new_user: false,
        }),
      }),
    );
    await page.route("**/api/projects", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      }),
    );
    await page.goto("/app/products");
    await expect(page.getByTestId("product-portfolio-page")).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "One workspace. A growing product ecosystem.",
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "OraOne AI Chat Platform" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "OraOne OS" }),
    ).toBeVisible();
    expect(await page.getByText("Planned", { exact: true }).count()).toBe(8);
    await expect(
      page.getByText("Long-term vision", { exact: true }),
    ).toBeVisible();
  });
});
