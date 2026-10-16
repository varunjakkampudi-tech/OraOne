import { expect, test } from "./fixtures";
import { signInAsDevUser } from "./helpers";

// Every internal link on the main screens must lead to a real page. A link that
// returns 404 is a broken navigation path, so the sweep fails on the first one.
async function internalLinks(page: import("@playwright/test").Page): Promise<string[]> {
  return page.$$eval("a[href]", (anchors) =>
    anchors
      .map((a) => a.getAttribute("href") ?? "")
      .filter((href) => href.startsWith("/") && !href.startsWith("//"))
      .map((href) => (href.split("#")[0] ?? "").split("?")[0] ?? "")
      .filter((href): href is string => Boolean(href)),
  );
}

test.describe("@regression internal link sweep", () => {
  test("every link on public pages resolves @regression", async ({ page }) => {
    const pages = [
      "/",
      "/pricing",
      "/products/ai-chat",
      "/about",
      "/security",
      "/contact",
      "/docs",
      "/help",
    ];
    const found = new Set<string>();
    for (const route of pages) {
      await page.goto(route);
      for (const href of await internalLinks(page)) found.add(href);
    }
    const broken: string[] = [];
    for (const href of found) {
      if (href.includes("$")) continue;
      const response = await page.request.get(href, { maxRedirects: 0 });
      if (response.status() >= 400) broken.push(`${response.status()} ${href}`);
    }
    expect(found.size).toBeGreaterThan(10);
    expect(broken).toEqual([]);
  });

  test("every link in the studio resolves @regression", async ({ page }) => {
    await signInAsDevUser(page);
    const found = new Set<string>();
    for (const route of ["/studio", "/studio/inbox", "/studio/leads", "/studio/knowledge"]) {
      await page.goto(route);
      for (const href of await internalLinks(page)) found.add(href);
    }
    const broken: string[] = [];
    for (const href of found) {
      if (href.includes("$")) continue;
      const response = await page.request.get(href, { maxRedirects: 0 });
      if (response.status() >= 400) broken.push(`${response.status()} ${href}`);
    }
    expect(broken).toEqual([]);
  });
});
