import { readdirSync } from "node:fs";
import { resolve } from "node:path";
import type { Page, Route } from "@playwright/test";
import { expect, test } from "./fixtures";
import { expectNoHorizontalScroll, mockStudioApi, trackPageErrors } from "./product-support";

/**
 * Route health: every page file in src/routes must load a real screen.
 *
 * Paths follow TanStack file routing: dotted names become segments, `index` is the parent
 * path, `$param` is filled with the sample id "demo", a trailing `_` escapes the parent
 * layout, and `_`-prefixed directories (for example `_authenticated/`) are pathless.
 * `__root.tsx` and `route.tsx` layouts are not URLs and are skipped.
 *
 * Every /api request is answered in the browser. The signed-in fake organization comes from
 * mockStudioApi (e2e/product-support.ts). Any other GET gets an empty list page so screens
 * render their empty states. Nothing reaches a backend. The 390 and 1280 projects each visit
 * every route at their own width; the 768 project is skipped.
 */

const ERROR_BOUNDARY_TEXT = [
  /Something went wrong/i,
  /This page didn't load/i,
  /This page could not load/i,
];

const SAMPLE_ID = "demo";

// GET paths that mockStudioApi answers itself. Anything else under /api gets an empty list.
const PATHS_ANSWERED_BY_SHARED_MOCK = [
  /^\/api\/auth\/me$/,
  /^\/api\/auth\/identity$/,
  /^\/api\/projects$/,
  /^\/api\/conversations$/,
  /^\/api\/agents(\/[^/]+)?$/,
  /^\/api\/widgets(\/[^/]+\/analytics)?$/,
  /^\/api\/billing\/(subscription|plans)$/,
  /^\/api\/usage$/,
  /^\/api\/leads(\/stats)?$/,
  /^\/api\/team\/(members|invitations)$/,
  /^\/api\/calls\/campaigns$/,
  /^\/api\/workflows$/,
];

function walk(dir: string, prefix = ""): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) return walk(resolve(dir, entry.name), rel);
    return entry.name.endsWith(".tsx") ? [rel] : [];
  });
}

/** Maps a file under src/routes (relative path) to its URL path, or null when it is not a page. */
function routePathFor(file: string): string | null {
  const parts = file.split("/");
  const name = parts.pop() ?? "";
  if (name.startsWith("__") || name === "route.tsx") return null;
  const base = name.replace(/\.tsx$/, "");
  const segments = base
    .split(".")
    .filter((segment) => segment !== "index")
    .map((segment) => segment.replace(/_$/, ""))
    .map((segment) => (segment.startsWith("$") ? SAMPLE_ID : segment));
  return "/" + segments.join("/");
}

// Every channel setup page is visited by its real key, not only the sample id.
const CHANNEL_PATHS = [
  "/studio/channels/website-chat",
  "/studio/channels/whatsapp",
  "/studio/channels/instagram",
  "/studio/channels/voice",
];

const ROUTES = Array.from(
  new Set(
    walk(resolve(process.cwd(), "src/routes"))
      .map(routePathFor)
      .filter((path): path is string => path !== null)
      .concat(CHANNEL_PATHS),
  ),
).sort();

const EMPTY_ANALYTICS = {
  range_days: 30,
  generated_at: "2026-10-17T00:00:00Z",
  totals: {
    agents: 0,
    conversations: 0,
    messages: 0,
    workflows: 0,
    workflow_runs: 0,
    knowledge_bases: 0,
    documents: 0,
    members: 0,
    qualified_conversations: 0,
    conversion_rate: 0,
  },
  series: { conversations: [], messages: [], workflow_runs: [] },
  breakdowns: {
    conversations_by_channel: {},
    conversations_by_status: {},
    workflow_runs_by_status: {},
  },
  top_agents: [],
};

// Empty responses in the shape each screen reads. Paths not listed here get an empty list.
const EMPTY_SHAPES: Array<{ pattern: RegExp; body: unknown }> = [
  { pattern: /^\/api\/analytics\/overview$/, body: EMPTY_ANALYTICS },
  { pattern: /^\/api\/api-keys$/, body: { keys: [], scopes: [] } },
  { pattern: /^\/api\/webhooks$/, body: { webhooks: [], events: [] } },
  { pattern: /^\/api\/marketplace\/listings$/, body: [] },
  { pattern: /^\/api\/conversations\/[^/]+\/messages$/, body: [] },
  {
    pattern: /^\/api\/conversations\/[^/]+$/,
    body: {
      id: "00000000-0000-4000-8000-0000000000c1",
      agent_id: "00000000-0000-4000-8000-0000000000a1",
      channel: "chat",
      title: "Example conversation",
      status: "open",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      last_message_at: null,
      is_archived: false,
    },
  },
];

/** Fake /api answers layered over mockStudioApi. Mutations are refused by the shared mock. */
async function mockApi(page: Page, signedIn = true): Promise<void> {
  await mockStudioApi(page);
  await page.route("**/api/**", async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (!url.pathname.startsWith("/api/")) return route.fallback();
    if (url.pathname === "/api/auth/me" && !signedIn) {
      return route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Not signed in" }),
      });
    }
    if (request.method() !== "GET") return route.fallback();
    if (PATHS_ANSWERED_BY_SHARED_MOCK.some((re) => re.test(url.pathname))) {
      return route.fallback();
    }
    const shape = EMPTY_SHAPES.find((entry) => entry.pattern.test(url.pathname));
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(shape ? shape.body : { items: [], total: 0 }),
    });
  });
}

test.describe("route health", () => {
  test.beforeEach(({ browserName: _browserName }, testInfo) => {
    test.skip(testInfo.project.name === "768", "Covered at 390 and 1280 only.");
  });

  for (const path of ROUTES) {
    test(`${path} loads a real screen`, async ({ page }, testInfo) => {
      await mockApi(page);
      const errors = trackPageErrors(page);

      const response = await page.goto(path, { waitUntil: "load", timeout: 90_000 });
      expect(response?.status(), `HTTP status for ${path}`).toBe(200);

      // A real screen has more than a loader label. Wait past lazy-route loaders ("Loading page").
      await page.waitForFunction(
        () => document.body.innerText.replace(/Loading[^\n]*/g, "").trim().length > 20,
        undefined,
        { timeout: 60_000 },
      );
      // Let lazy chunks and the mocked data calls settle before reading the page.
      await page.waitForTimeout(1_000);

      const text = await page.locator("body").innerText();
      for (const pattern of ERROR_BOUNDARY_TEXT) {
        expect(text, `error boundary text on ${path}`).not.toMatch(pattern);
      }
      expect(errors, `uncaught page errors on ${path}`).toEqual([]);

      if (testInfo.project.name === "390") {
        await expectNoHorizontalScroll(page);
      }
    });
  }
});

test.describe("protected studio routes", () => {
  test("redirect to sign-in when the session is rejected", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "390", "Redirect checked once, at phone width.");
    await mockApi(page, false);
    await page.goto("/studio", { waitUntil: "load", timeout: 90_000 });
    await page.waitForURL(/\/auth\/sign-in/, { timeout: 60_000 });
  });
});
