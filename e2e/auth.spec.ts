import { expect, test } from "./fixtures";
import { expectNoHorizontalScroll, trackPageErrors, waitForHydration } from "./product-support";

// Smoke check for sign-in. Auth is passwordless: an emailed code, never a password.
// Nothing is submitted, so no code is requested and no account is touched.

test.describe("sign-in smoke", () => {
  test("sign-in shows the email code form and no password field", async ({ page }) => {
    const errors = trackPageErrors(page);

    await page.goto("/auth/sign-in");
    await waitForHydration(page);

    const emailCodeForm = page
      .locator("form")
      .filter({ has: page.getByRole("button", { name: "Email me a code" }) });
    await expect(emailCodeForm.getByRole("textbox", { name: /email/i })).toBeVisible();
    await expect(emailCodeForm.getByRole("button", { name: "Email me a code" })).toBeVisible();
    // The email-code form itself has no password input. The development-only
    // password panel (DevSignIn) renders on dev builds outside this form and is
    // deliberately not checked here.
    await expect(emailCodeForm.locator('input[type="password"]')).toHaveCount(0);
    await expectNoHorizontalScroll(page);
    expect(errors, "no uncaught page errors").toEqual([]);
  });
});
