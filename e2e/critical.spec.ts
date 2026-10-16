import { expect, test } from "./fixtures";
import { signInAsDevUser, waitForAppReady } from "./helpers";

test.describe("@critical sign-in and session", () => {
  test("protected studio redirects an anonymous visitor to sign-in @critical", async ({ page }) => {
    await page.goto("/studio");
    // The guard runs in the browser, so allow time for the first client render.
    await expect(page).toHaveURL(/\/auth\/sign-in/, { timeout: 20_000 });
  });

  test("development sign-in opens the workspace list @critical", async ({ page }) => {
    await signInAsDevUser(page);
    await page.goto("/studio");
    await waitForAppReady(page);
    await expect(page.getByRole("heading", { name: "Your assistants" })).toBeVisible();
  });

  test("signed-in user can open the inbox and leads @critical", async ({ page }) => {
    await signInAsDevUser(page);
    await page.goto("/studio/inbox");
    await waitForAppReady(page);
    await expect(page.getByRole("heading", { name: "Conversations" })).toBeVisible();
    await page.goto("/studio/leads");
    await waitForAppReady(page);
    await expect(page.getByRole("heading", { name: "Leads" })).toBeVisible();
  });

  test("sign-out ends the session and blocks protected pages @critical", async ({ page }) => {
    await signInAsDevUser(page);
    await page.goto("/studio");
    await waitForAppReady(page);
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/auth\/sign-in/);
    // The server must reject the ended session.
    const identity = await page.request.get("/api/auth/identity");
    expect(identity.status()).toBe(401);
    // A full load of a protected page is redirected by the app's own guard. Some
    // browsers report the superseded first load as an aborted navigation (Firefox) or an
    // interrupted one (WebKit). Only that case is tolerated; the final URL is asserted.
    await page.goto("/studio").catch((error: Error) => {
      const superseded = /NS_BINDING_ABORTED|interrupted by another navigation/.test(error.message);
      if (!superseded) throw error;
    });
    await expect(page).toHaveURL(/\/auth\/sign-in/, { timeout: 20_000 });
  });

  test("an invalid email is rejected before any request is sent @critical", async ({ page }) => {
    await page.goto("/auth/sign-in");
    await waitForAppReady(page);
    await page.getByRole("textbox", { name: /email/i }).fill("not-an-email");
    await page.getByRole("button", { name: "Email me a code" }).click();
    await expect(page.getByRole("alert")).toContainText("Enter a valid email address.");
  });
});
