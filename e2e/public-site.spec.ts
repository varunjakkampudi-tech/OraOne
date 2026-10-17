import { expect, test } from "./fixtures";
import { expectNoHorizontalScroll, trackPageErrors, waitForHydration } from "./product-support";

// Public marketing, docs and legal pages. Each runs at the 390, 768 and 1280
// widths defined in playwright.config.ts.
const PUBLIC_PAGES: Array<{ path: string; name: string }> = [
  { path: "/", name: "homepage" },
  { path: "/products", name: "products" },
  { path: "/pricing", name: "pricing" },
  { path: "/docs", name: "docs" },
  { path: "/contact", name: "contact" },
  { path: "/privacy", name: "privacy policy" },
  { path: "/terms", name: "terms of service" },
  { path: "/cookies", name: "cookie policy" },
];

test.describe("public site", () => {
  for (const entry of PUBLIC_PAGES) {
    test(`${entry.name} renders a heading without scroll or page errors`, async ({ page }) => {
      const errors = trackPageErrors(page);

      const response = await page.goto(entry.path);
      expect(response?.status(), `${entry.path} should load`).toBeLessThan(400);

      await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
      await waitForHydration(page);
      await expectNoHorizontalScroll(page);
      expect(errors, "no uncaught page errors").toEqual([]);
    });
  }
});
