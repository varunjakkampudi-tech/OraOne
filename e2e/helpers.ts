import { expect, type Page } from "@playwright/test";

/** Local development account seeded by backend/scripts/seed_dev_users.py. */
export const DEV_USER = { email: "varun@oraone.in", password: "varun@oraone.in" } as const;

/**
 * Sign in through the development endpoint. The browser context receives the
 * httpOnly session cookies, exactly as after a real sign-in.
 */
export async function signInAsDevUser(page: Page, account = DEV_USER): Promise<void> {
  const response = await page.request.post("/api/auth/dev-login", {
    data: { email: account.email, password: account.password },
  });
  expect(response.status(), "dev sign-in must succeed; run scripts/seed_dev_users.py").toBe(200);
  // The product's sign-in also provisions the account's organization and workspace.
  const identity = await page.request.get("/api/auth/identity");
  expect(identity.status(), "identity must be provisioned after sign-in").toBe(200);
}

/** Wait until the page has finished its initial client-side render. */
export async function waitForAppReady(page: Page): Promise<void> {
  await page.waitForLoadState("load");
  // Interactions must wait for hydration: before it, a form submits natively.
  // React attaches a props object to interactive elements only once hydrated.
  await page.waitForFunction(
    () =>
      Array.from(document.querySelectorAll("button, a, input")).some((el) =>
        Object.keys(el).some((key) => key.startsWith("__reactProps")),
      ),
    undefined,
    { timeout: 20_000 },
  );
}

/** True when every <img> on the page has loaded (no broken or missing images). */
export async function brokenImages(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    Array.from(document.images)
      .filter((img) => img.complete && img.naturalWidth === 0)
      .map((img) => img.getAttribute("src") ?? "(no src)"),
  );
}

/**
 * Create a throwaway assistant for a test and return its id. Pair it with
 * deleteTestAssistant in afterEach so repeated runs leave no clutter behind.
 */
export async function createTestAssistant(page: Page, name: string): Promise<string> {
  const projects = await page.request.get("/api/projects?limit=5");
  const projectId = (await projects.json()).items[0].id as string;
  const created = await page.request.post("/api/agents", {
    headers: { "X-Project-Id": projectId },
    data: { name, type: "chat", description: "Customer support", model: "openai/gpt-5.5" },
  });
  if (created.status() !== 201)
    throw new Error(`Could not create test assistant: ${created.status()}`);
  return (await created.json()).id as string;
}

/** Soft-delete an assistant created by createTestAssistant. */
export async function deleteTestAssistant(page: Page, agentId: string): Promise<void> {
  await page.request.delete(`/api/agents/${agentId}`);
}
