import { expect, test } from "./fixtures";
import { waitForAppReady } from "./helpers";

test.describe("@regression navigation and interactions", () => {
  test("desktop product menu opens and lists Product 1 @regression", async ({ page, isMobile }) => {
    test.skip(isMobile, "Desktop navigation is hidden on mobile widths.");
    await page.goto("/");
    await waitForAppReady(page);
    const nav = page.getByRole("navigation", { name: "Main navigation" });
    await nav.getByRole("button", { name: "Products" }).click();
    await expect(page.getByRole("menu")).toBeVisible();
    await expect(page.getByRole("menu").getByText("AI Chat")).toBeVisible();
  });

  test("main navigation link goes to pricing @regression", async ({ page, isMobile }) => {
    test.skip(isMobile, "Desktop navigation is hidden on mobile widths.");
    await page.goto("/");
    await waitForAppReady(page);
    await page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: "Pricing" })
      .click();
    await expect(page).toHaveURL(/\/pricing$/);
  });

  test("mobile menu opens and navigates @regression", async ({ page, isMobile }) => {
    test.skip(!isMobile, "The mobile menu is only shown at narrow widths.");
    await page.goto("/");
    await waitForAppReady(page);
    await page.getByRole("button", { name: "Open navigation" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("link", { name: "Pricing" }).click();
    await expect(page).toHaveURL(/\/pricing$/);
  });

  test("product tour video is opt-in and has playable sources @regression", async ({ page }) => {
    await page.goto("/");
    await waitForAppReady(page);
    await expect(page.locator("video.app-tour-video")).toHaveCount(0);
    const start = page.getByRole("button", { name: "Play the sample tour" });
    await start.scrollIntoViewIfNeeded();
    await start.click();
    const video = page.locator("video.app-tour-video");
    await expect(video).toBeVisible();
    const sources = await video
      .locator("source")
      .evaluateAll((nodes) => nodes.map((node) => (node as HTMLSourceElement).src));
    expect(sources.length).toBeGreaterThanOrEqual(2);
    for (const src of sources) {
      const response = await page.request.get(src);
      expect(response.ok(), `video source ${src} must load`).toBeTruthy();
    }
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
