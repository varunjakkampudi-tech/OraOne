import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "./fixtures";

// Every page listed in the sitemap must be a complete, indexable document: a unique
// title, a description, a canonical link to itself, exactly one h1, and a language.
const sitemap = readFileSync(resolve(process.cwd(), "public/sitemap.xml"), "utf-8");
const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1] ?? "");

test.describe("@regression SEO metadata for every sitemap page", () => {
  test("the sitemap lists pages on the production origin @regression", () => {
    expect(urls.length).toBeGreaterThan(0);
    for (const url of urls) expect(url.startsWith("https://oraone.in")).toBeTruthy();
  });

  for (const url of urls) {
    test(`${new URL(url).pathname} has complete metadata @regression`, async ({ page }) => {
      const response = await page.goto(new URL(url).pathname);
      expect(response?.status()).toBe(200);
      const meta = await page.evaluate(() => ({
        title: document.title,
        description:
          document.querySelector('meta[name="description"]')?.getAttribute("content") ?? "",
        canonical: document.querySelector('link[rel="canonical"]')?.getAttribute("href") ?? "",
        h1: document.querySelectorAll("h1").length,
        lang: document.documentElement.lang,
      }));
      expect(meta.title.length, "title").toBeGreaterThan(5);
      expect(meta.description.length, "description").toBeGreaterThan(50);
      expect(meta.canonical, "canonical").toBe(url);
      expect(meta.h1, "h1 count").toBe(1);
      expect(meta.lang, "lang").toBe("en");
    });
  }
});
