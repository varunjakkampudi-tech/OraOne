import { expect, test } from "./fixtures";
import {
  expectNoHorizontalScroll,
  waitForHydration,
  MOCK_AGENT_ID,
  mockStudioApi,
  trackPageErrors,
} from "./product-support";

// Install page for an assistant. The mock reports a published widget that no
// visitor has loaded yet, so the page must show the waiting state.

test.describe("assistant install page with mocked API", () => {
  test.beforeEach(async ({ page }) => {
    await mockStudioApi(page);
  });

  test("shows the copy-snippet control and waits for the first visit", async ({ page }) => {
    const errors = trackPageErrors(page);

    await page.goto(`/studio/assistants/${MOCK_AGENT_ID}/install`);
    await waitForHydration(page);

    await expect(page.getByRole("button", { name: "Copy code" }).first()).toBeVisible();
    await expect(
      page.getByRole("status").filter({ hasText: "Waiting for first visit" }),
    ).toBeVisible();
    await expectNoHorizontalScroll(page);
    expect(errors, "no uncaught page errors").toEqual([]);
  });
});
