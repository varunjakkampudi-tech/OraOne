import { expect, test } from "./fixtures";
import { waitForAppReady } from "./helpers";

/**
 * Screenshot comparisons for key layouts. The first run creates the baselines
 * in e2e/visual.spec.ts-snapshots/. Review them, then commit them. A later
 * change that moves the logo, hero or navigation fails the comparison.
 */
test.describe("@visual key layouts", () => {
  test("home page layout @visual", async ({ page, isMobile }) => {
    test.skip(isMobile, "Mobile layouts are compared in their own project.");
    await page.goto("/");
    await waitForAppReady(page);
    await expect(page).toHaveScreenshot("home.png", { fullPage: false });
  });

  test("home page layout on phones @visual", async ({ page, isMobile }) => {
    test.skip(!isMobile, "Phone layout is compared on mobile projects only.");
    await page.goto("/");
    await waitForAppReady(page);
    await expect(page).toHaveScreenshot("home-mobile.png", { fullPage: false });
  });

  test("sign-in layout @visual", async ({ page, isMobile }) => {
    test.skip(isMobile, "Compared on desktop only.");
    await page.goto("/auth/sign-in");
    await waitForAppReady(page);
    await expect(page).toHaveScreenshot("sign-in.png", { fullPage: false });
  });

  test("sample dashboard layout @visual", async ({ page, isMobile }) => {
    test.skip(isMobile, "Compared on desktop only.");
    await page.goto("/app");
    await waitForAppReady(page);
    await expect(page).toHaveScreenshot("app-overview.png", { fullPage: false });
  });
});
