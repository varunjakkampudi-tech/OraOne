import { expect, test } from "./fixtures";
import { expectNoHorizontalScroll, trackPageErrors, waitForHydration } from "./product-support";

// The Admin Console is not connected to a staff identity service yet, so it
// opens only as a labelled design preview with sample data and no actions.

test.describe("admin design preview", () => {
  test("the preview opens with a restricted notice and no real access", async ({ page }) => {
    const errors = trackPageErrors(page);

    await page.goto("/admin?preview=design");
    await waitForHydration(page);

    const notice = page.getByRole("status").filter({ hasText: "Design preview" });
    await expect(notice).toBeVisible();
    await expect(notice).toContainText("not signed in, no admin permissions");
    await expectNoHorizontalScroll(page);
    expect(errors, "no uncaught page errors").toEqual([]);
  });

  test("the users table reports that its data source is not connected", async ({ page }) => {
    const errors = trackPageErrors(page);

    // Same tab: the preview flag is kept in sessionStorage, so this child route stays open.
    await page.goto("/admin?preview=design");
    await waitForHydration(page);
    await page.goto("/admin/users");
    await waitForHydration(page);

    await expect(page.getByRole("heading", { level: 1, name: "Users" })).toBeVisible();
    await expect(page.getByText("No records loaded · Data source not connected")).toBeVisible();
    await expectNoHorizontalScroll(page);
    expect(errors, "no uncaught page errors").toEqual([]);
  });
});
