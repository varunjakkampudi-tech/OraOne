import type { Page } from "@playwright/test";
import { expect, test } from "./fixtures";
import { signInAsDevUser, waitForAppReady } from "./helpers";

// Clicks every visible button on a screen and fails on any uncaught JavaScript error.
// Controls that change real data, end the session or submit a form are skipped by
// name, so the sweep is safe to run repeatedly.
const UNSAFE =
  /sign out|log ?out|delete|remove|send|submit|save|publish|pause|create|invite|upgrade|subscribe|pay|revoke|regenerate|sign in|email me|continue|verify|reset|cancel plan|purchase/i;

async function sweep(page: Page, route: string) {
  const errors: string[] = [];
  const onError = (error: Error) => errors.push(error.message);
  page.on("pageerror", onError);
  await page.goto(route);
  await waitForAppReady(page);
  const count = await page.locator("button:visible").count();
  const clicked: string[] = [];
  for (let index = 0; index < count; index += 1) {
    // Reload only after a click has navigated away, so each control starts from the same screen.
    if (new URL(page.url()).pathname !== new URL(route, page.url()).pathname) {
      await page.goto(route);
      await waitForAppReady(page);
    }
    // Close any menu the previous control opened.
    await page.keyboard.press("Escape").catch(() => undefined);
    const button = page.locator("button:visible").nth(index);
    if ((await button.count()) === 0) continue;
    const label =
      ((await button.textContent()) ?? "").trim() ||
      (await button.getAttribute("aria-label")) ||
      `button ${index}`;
    if (UNSAFE.test(label) || !(await button.isEnabled())) continue;
    await button.click({ timeout: 5_000 }).catch(() => undefined);
    clicked.push(label);
  }
  page.off("pageerror", onError);
  expect(errors, `errors on ${route} after clicking: ${clicked.join(", ")}`).toEqual([]);
}

test.describe("@regression control sweep", () => {
  for (const route of ["/", "/pricing", "/products/ai-chat", "/app"]) {
    test(`buttons on ${route} respond without errors @regression`, async ({ page }) => {
      await sweep(page, route);
    });
  }

  test("buttons on signed-in studio screens respond without errors @regression", async ({
    page,
  }) => {
    // Eight screens with a reload per button need more than the default two minutes.
    test.setTimeout(540_000);
    await signInAsDevUser(page);
    for (const route of [
      "/studio",
      "/studio/inbox",
      "/studio/leads",
      "/studio/knowledge",
      "/studio/analytics",
      "/studio/team",
      "/studio/billing",
      "/studio/account",
    ]) {
      await sweep(page, route);
    }
  });
});
