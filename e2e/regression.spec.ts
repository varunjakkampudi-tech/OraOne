import { expect, test } from "./fixtures";
import { waitForAppReady } from "./helpers";

test.describe("@regression navigation and interactions", () => {
  test("desktop product menu opens and lists Product 1 @regression", async ({ page, isMobile }) => {
    test.skip(isMobile, "Desktop navigation is hidden on mobile widths.");
    await page.goto("/");
    await waitForAppReady(page);
    const nav = page.getByRole("navigation", { name: "Main" });
    await nav.getByText("Products", { exact: true }).click();
    await expect(nav.getByRole("link", { name: "AI Chat" })).toBeVisible();
  });

  test("main navigation link goes to pricing @regression", async ({ page, isMobile }) => {
    test.skip(isMobile, "Desktop navigation is hidden on mobile widths.");
    await page.goto("/");
    await waitForAppReady(page);
    await page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Pricing" })
      .click();
    await expect(page).toHaveURL(/\/pricing$/);
  });

  test("mobile menu opens and navigates @regression", async ({ page, isMobile }) => {
    test.skip(!isMobile, "The mobile menu is only shown at narrow widths.");
    await page.goto("/");
    await waitForAppReady(page);
    await page.getByRole("button", { name: "Open menu" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("link", { name: "Pricing" }).click();
    await expect(page).toHaveURL(/\/pricing$/);
  });

  test("home page labels each capability with its status @regression", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("Available", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("In development", { exact: true }).first()).toBeVisible();
  });

  test("unknown route shows the not-found page @regression", async ({ page }) => {
    const response = await page.goto("/this-page-does-not-exist");
    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Go home" })).toBeVisible();
  });

  test("workspace tabs switch sections without a reload @regression", async ({
    page,
    isMobile,
  }) => {
    test.skip(isMobile, "The workspace sidebar is hidden at phone widths.");
    await page.goto("/app");
    await waitForAppReady(page);
    await page.getByRole("link", { name: "Unified Inbox" }).first().click();
    await expect(page).toHaveURL(/\/app\/inbox/);
  });
});
