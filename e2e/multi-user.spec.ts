import type { Browser, BrowserContext, Page } from "@playwright/test";
import { expect, test } from "./fixtures";
import {
  createTestAssistant,
  deleteTestAssistant,
  DEV_USER,
  signInAsDevUser,
  waitForAppReady,
} from "./helpers";

// Two people sign in from separate browser sessions. Each creates an assistant, and
// neither may see the other's data in the UI or through the API. Each session has its
// own cookies, so the two accounts never share a login.
const SECOND_USER = { email: "admin@oraone.in", password: "oraone.in" } as const;

async function openSession(
  browser: Browser,
  account: { readonly email: string; readonly password: string },
) {
  const context: BrowserContext = await browser.newContext({
    baseURL: process.env["E2E_BASE_URL"] ?? "http://localhost:5180",
  });
  const page: Page = await context.newPage();
  await signInAsDevUser(page, account);
  return { context, page };
}

test.describe("@regression multi-user isolation", () => {
  test("each user sees only their own assistants @regression", async ({ browser }) => {
    const first = await openSession(browser, DEV_USER);
    const second = await openSession(browser, SECOND_USER);
    const firstName = `Isolation A ${Date.now()}`;
    const secondName = `Isolation B ${Date.now()}`;
    const firstId = await createTestAssistant(first.page, firstName);
    const secondId = await createTestAssistant(second.page, secondName);
    try {
      // The UI lists only the signed-in user's assistants.
      await first.page.goto("/studio");
      await waitForAppReady(first.page);
      await expect(first.page.getByRole("link", { name: firstName })).toBeVisible();
      await expect(first.page.getByText(secondName)).toHaveCount(0);

      await second.page.goto("/studio");
      await waitForAppReady(second.page);
      await expect(second.page.getByRole("link", { name: secondName })).toBeVisible();
      await expect(second.page.getByText(firstName)).toHaveCount(0);

      // Direct API access to another user's assistant is refused.
      const crossRead = await second.page.request.get(`/api/agents/${firstId}`);
      expect(crossRead.status(), "second user reads first user's assistant").toBeGreaterThanOrEqual(
        400,
      );
      const crossWrite = await first.page.request.get(`/api/agents/${secondId}`);
      expect(
        crossWrite.status(),
        "first user reads second user's assistant",
      ).toBeGreaterThanOrEqual(400);
    } finally {
      await deleteTestAssistant(first.page, firstId);
      await deleteTestAssistant(second.page, secondId);
      await first.context.close();
      await second.context.close();
    }
  });

  test("two sessions for one user stay signed in independently @regression", async ({
    browser,
  }) => {
    const first = await openSession(browser, DEV_USER);
    const second = await openSession(browser, DEV_USER);
    try {
      await first.page.goto("/studio");
      await waitForAppReady(first.page);
      await first.page.getByRole("button", { name: "Sign out" }).click();
      await expect(first.page).toHaveURL(/\/auth\/sign-in/);
      // Signing out in one browser must not end the other browser's session.
      const stillSignedIn = await second.page.request.get("/api/auth/identity");
      expect(stillSignedIn.status()).toBe(200);
    } finally {
      await first.context.close();
      await second.context.close();
    }
  });
});
