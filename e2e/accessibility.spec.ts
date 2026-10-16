import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./fixtures";
import { signInAsDevUser, waitForAppReady } from "./helpers";

// WCAG 2.1 AA is the standard OraOne commits to. Serious and critical findings fail
// the build; moderate and minor findings are reported in the test output.
const STANDARDS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function auditPage(page: import("@playwright/test").Page, label: string) {
  await waitForAppReady(page);
  const results = await new AxeBuilder({ page }).withTags(STANDARDS).analyze();
  const blocking = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
  for (const v of results.violations) {
    console.log(`[a11y] ${label} ${v.impact} ${v.id}: ${v.help} (${v.nodes.length} nodes)`);
    for (const n of v.nodes) {
      console.log(
        `[a11y-node] ${label} ${n.target.join(" ")} :: ${n.html.slice(0, 60)} :: ${(n.failureSummary ?? "").replace(/s+/g, " ").slice(0, 300)}`,
      );
    }
  }
  return blocking;
}

test.describe("@regression accessibility (WCAG 2.1 AA)", () => {
  const publicRoutes = [
    "/",
    "/pricing",
    "/auth/sign-in",
    "/auth/sign-up",
    "/this-page-does-not-exist",
  ];

  for (const route of publicRoutes) {
    test(`public page ${route} has no serious or critical violations @regression`, async ({
      page,
    }) => {
      await page.goto(route);
      const blocking = await auditPage(page, route);
      expect(blocking.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
    });
  }

  test("studio home has no serious or critical violations @regression", async ({ page }) => {
    await signInAsDevUser(page);
    await page.goto("/studio");
    const blocking = await auditPage(page, "/studio");
    expect(blocking.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
  });

  test("studio inbox and leads have no serious or critical violations @regression", async ({
    page,
  }) => {
    await signInAsDevUser(page);
    for (const route of ["/studio/inbox", "/studio/leads", "/studio/knowledge"]) {
      await page.goto(route);
      const blocking = await auditPage(page, route);
      expect(
        blocking.map((v) => `${v.id}: ${v.help}`),
        route,
      ).toEqual([]);
    }
  });

  test("sample workspace and install screen have no serious or critical violations @regression", async ({
    page,
  }) => {
    await page.goto("/app");
    const sample = await auditPage(page, "/app");
    expect(sample.map((v) => `${v.id}: ${v.help}`)).toEqual([]);

    await signInAsDevUser(page);
    const projects = await page.request.get("/api/projects?limit=5");
    const projectId = (await projects.json()).items[0].id as string;
    const created = await page.request.post("/api/agents", {
      headers: { "X-Project-Id": projectId },
      data: {
        name: `A11y ${Date.now()}`,
        type: "chat",
        description: "Customer support",
        model: "openai/gpt-5.5",
      },
    });
    const agentId = (await created.json()).id as string;
    await page.goto(`/studio/assistants/${agentId}/install`);
    const install = await auditPage(page, "/install");
    expect(install.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
  });
});
