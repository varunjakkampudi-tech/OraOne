import { expect, test } from "./fixtures";
import { signInAsDevUser, waitForAppReady } from "./helpers";

test.describe("@regression website widget", () => {
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
    const projects = await page.request.get("/api/projects?limit=5");
    const projectId = (await projects.json()).items[0].id as string;
    const name = `Widget test ${Date.now()}`;
    const created = await page.request.post("/api/agents", {
      headers: { "X-Project-Id": projectId },
      data: { name, type: "chat", description: "Customer support", model: "openai/gpt-5.5" },
    });
    expect(created.status()).toBe(201);
    const agentId = (await created.json()).id as string;

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
