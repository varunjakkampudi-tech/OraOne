import { expect, test } from "./fixtures";
import { brokenImages, waitForAppReady } from "./helpers";

test.describe("@smoke core pages render", () => {
  test("home page shows the brand, hero and headline @smoke", async ({ page }) => {
    await page.goto("/");
    await waitForAppReady(page);
    await expect(page).toHaveTitle(/OraOne/);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(await brokenImages(page)).toEqual([]);
  });

  test("logo image loads on the home page @smoke", async ({ page }) => {
    await page.goto("/");
    const logo = page.getByRole("img", { name: "OraOne logo" }).first();
    await expect(logo).toBeVisible();
    await expect
      .poll(() => logo.evaluate((img: HTMLImageElement) => img.naturalWidth))
      .toBeGreaterThan(0);
  });

  test("hero illustration is shown on the home page @smoke", async ({ page }) => {
    await page.goto("/");
    const hero = page.getByRole("img", { name: /Illustration: a visitor/ });
    await expect(hero).toBeVisible();
  });

  test("sign-in page offers the email code form @smoke", async ({ page }) => {
    await page.goto("/auth/sign-in");
    await expect(page.getByRole("textbox", { name: /email/i })).toBeVisible();
    await expect(page.getByRole("button", { name: "Email me a code" })).toBeVisible();
  });

  test("sample workspace loads @smoke", async ({ page }) => {
    await page.goto("/app");
    await waitForAppReady(page);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });
});
