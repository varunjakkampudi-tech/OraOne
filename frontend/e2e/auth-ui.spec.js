const { test, expect } = require("@playwright/test");

test.describe("OraOne authentication presentation", () => {
  test("desktop sign-in uses the brand and clearly labeled workspace preview", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1440, height: 960 });
    await page.goto("/login");

    await expect(page.getByTestId("auth-page")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Welcome Back" }),
    ).toBeVisible();
    await expect(page.getByText("Illustrative preview")).toBeVisible();
    await expect(page.getByText("No social sign-in")).toBeVisible();
    await expect(page.getByText(/Google|Continue with Google/i)).toHaveCount(0);
    await expect(
      page.locator('img[src="/assets/oraone-mark.png"]'),
    ).toHaveCount(2);
    await expect(page.locator("html")).toHaveJSProperty(
      "scrollWidth",
      await page.evaluate(() => window.innerWidth),
    );
  });

  test("signup keeps the custom page and email-only provider scope", async ({
    page,
  }) => {
    await page.goto("/signup");

    await expect(
      page.getByRole("heading", { name: "Create Your Account" }),
    ).toBeVisible();
    await expect(page.getByTestId("signup-form")).toBeVisible();
    await expect(page.getByRole("link", { name: "Sign in" })).toBeVisible();
    await expect(page.getByText(/Google|phone|social login/i)).toHaveCount(0);
  });

  test("mobile sign-in remains usable without horizontal overflow", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/login");

    await expect(page.getByTestId("login-form")).toBeVisible();
    await expect(page.getByTestId("login-email-input")).toBeVisible();
    await expect(page.getByTestId("login-password-input")).toBeVisible();

    const documentWidth = await page.evaluate(
      () => document.documentElement.scrollWidth,
    );
    expect(documentWidth).toBe(390);
  });
});
