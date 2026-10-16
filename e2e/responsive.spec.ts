import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";
import { signInAsDevUser, waitForAppReady } from "./helpers";

// Widths cover a small phone, a large phone, a tablet and a laptop.
const VIEWPORTS = [
  { name: "phone-360", width: 360, height: 740 },
  { name: "phone-390", width: 390, height: 844 },
  { name: "tablet-768", width: 768, height: 1024 },
  { name: "laptop-1280", width: 1280, height: 800 },
];

// Content must never widen the page: a horizontal scrollbar on a phone is a
// layout bug, so the document may not be wider than the viewport.
async function expectNoHorizontalOverflow(page: Page, label: string) {
  await waitForAppReady(page);
  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  expect(overflow.scrollWidth, `${label} overflows horizontally`).toBeLessThanOrEqual(
    overflow.clientWidth + 1,
  );
}

for (const viewport of VIEWPORTS) {
  test.describe(`@regression responsive ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    test("public pages fit the viewport @regression", async ({ page }) => {
      for (const route of [
        "/",
        "/pricing",
        "/products/ai-chat",
        "/auth/sign-in",
        "/auth/sign-up",
      ]) {
        await page.goto(route);
        await expectNoHorizontalOverflow(page, `${viewport.name} ${route}`);
      }
    });

    test("sample workspace fits the viewport @regression", async ({ page }) => {
      await page.goto("/app");
      await expectNoHorizontalOverflow(page, `${viewport.name} /app`);
    });

    test("studio screens fit the viewport @regression", async ({ page }) => {
      await signInAsDevUser(page);
      for (const route of ["/studio", "/studio/inbox", "/studio/leads", "/studio/knowledge"]) {
        await page.goto(route);
        await expectNoHorizontalOverflow(page, `${viewport.name} ${route}`);
      }
    });
  });
}
