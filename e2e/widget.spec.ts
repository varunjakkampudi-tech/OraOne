import { expect, test } from "./fixtures";
import {
  createTestAssistant,
  deleteTestAssistant,
  signInAsDevUser,
  waitForAppReady,
} from "./helpers";

test.describe("@regression website widget", () => {
  const created: string[] = [];
  test.afterEach(async ({ page }) => {
    for (const id of created.splice(0)) await deleteTestAssistant(page, id);
  });

  test("the embeddable loader is served as JavaScript @regression", async ({ page }) => {
    const response = await page.request.get("/widget.js");
    expect(response.ok()).toBeTruthy();
    expect(response.headers()["content-type"]).toContain("javascript");
    const body = await response.text();
    expect(body).toContain("data-widget-id");
    expect(body).toContain("window.OraOne");
  });

  test("install page offers the script tag, SDK and React code @regression", async ({ page }) => {
    await signInAsDevUser(page);
    const name = `Widget test ${Date.now()}`;
    const agentId = await createTestAssistant(page, name);
    created.push(agentId);

    await page.goto(`/studio/assistants/${agentId}/install`);
    await waitForAppReady(page);
    await expect(page.getByRole("heading", { name: `Add ${name} to your website` })).toBeVisible();

    await page.getByRole("button", { name: "Create chat widget" }).click();
    const scriptTab = page.getByRole("tab", { name: "Script tag" });
    await expect(scriptTab).toHaveAttribute("aria-selected", "true");
    await expect(page.locator("pre code").first()).toContainText("data-widget-id=");

    await page.getByRole("tab", { name: "Browser SDK" }).click();
    await expect(page.locator("pre code").first()).toContainText("window.OraOne");

    await page.getByRole("tab", { name: "React / Next.js" }).click();
    await expect(page.locator("pre code").first()).toContainText("useEffect");
  });
});
