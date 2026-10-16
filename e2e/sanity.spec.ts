import { expect, test } from "./fixtures";
import { brokenImages } from "./helpers";

/** Representative Product 1 routes: marketing, sample workspace, auth and legal. */
const SANITY_ROUTES = [
  "/",
  "/about",
  "/pricing",
  "/features",
  "/security",
  "/contact",
  "/docs",
  "/help",
  "/status",
  "/roadmap",
  "/products/ai-chat",
  "/solutions",
  "/auth/sign-in",
  "/auth/sign-up",
  "/app",
  "/app/inbox",
  "/app/leads",
  "/app/analytics",
  "/app/billing",
  "/app/settings",
  "/app/products/chat",
  "/app/products/chat/assistants",
  "/app/products/chat/knowledge",
  "/privacy",
  "/terms",
];

test.describe("@sanity every Product 1 route renders", () => {
  for (const route of SANITY_ROUTES) {
    test(`${route} responds and renders @sanity`, async ({ page }) => {
      const response = await page.goto(route);
      expect(response?.status(), `${route} status`).toBe(200);
      await expect(page).toHaveTitle(/\S/);
      await expect(page.locator("h1").first()).toBeVisible();
      expect(await brokenImages(page)).toEqual([]);
    });
  }
});
