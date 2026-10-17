import { expect, type Page, type Route } from "@playwright/test";

/**
 * Shared helpers for the product-surface suites (public-site, studio, admin,
 * install, auth). Everything here is fake: example.test addresses, a
 * "Mock Organization", and no real account or backend data.
 */

export const MOCK_ORG_NAME = "Mock Organization";
export const MOCK_AGENT_ID = "00000000-0000-4000-8000-0000000000a1";
export const MOCK_WIDGET_ID = "00000000-0000-4000-8000-0000000000b1";
export const MOCK_CONVERSATION_ID = "00000000-0000-4000-8000-0000000000c1";
const MOCK_PROJECT_ID = "00000000-0000-4000-8000-0000000000d1";
const MOCK_ORG_ID = "00000000-0000-4000-8000-0000000000e1";
const MOCK_USER_ID = "00000000-0000-4000-8000-000000000001";

const MOCK_ME = {
  userId: MOCK_USER_ID,
  email: "mock.user@example.test",
  name: "Mock User",
  role: "owner",
  platform_role: "user",
  plan: "starter",
  status: "active",
};

const MOCK_IDENTITY = {
  user: { id: MOCK_USER_ID, email: "mock.user@example.test", full_name: "Mock User" },
  organization: {
    id: MOCK_ORG_ID,
    name: MOCK_ORG_NAME,
    slug: "mock-organization",
    plan: "starter",
  },
  membership: { organization_id: MOCK_ORG_ID, role: "owner", status: "active" },
  is_new_user: false,
};

const MOCK_PROJECT = {
  id: MOCK_PROJECT_ID,
  name: "Mock workspace",
  slug: "mock-workspace",
  description: null,
  status: "active",
  is_default: true,
  settings: {},
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const MOCK_AGENT = {
  id: MOCK_AGENT_ID,
  organization_id: MOCK_ORG_ID,
  name: "Mock Assistant",
  description: "Example assistant for end-to-end tests",
  type: "chat",
  status: "active",
  model: "mock-model",
  system_prompt: null,
  temperature: 0.2,
  language: "en",
  greeting: "Hello from the mock assistant.",
  max_tokens: 512,
};

const MOCK_WIDGET = {
  id: MOCK_WIDGET_ID,
  public_key: "pk_mock_example_only",
  name: "Mock website widget",
  status: "published",
  agent_id: MOCK_AGENT_ID,
  domains: ["example.test"],
  embed_snippet: null,
  settings: {},
  theme: {},
  published_at: "2026-01-01T00:00:00Z",
  allowed_domains_required: false,
};

const MOCK_PLAN = {
  id: "00000000-0000-4000-8000-0000000000f1",
  code: "starter",
  name: "Starter",
  description: "Example plan for end-to-end tests",
  price_cents: 0,
  price_cents_yearly: 0,
  currency: "USD",
  features: [],
  limits: {},
  is_active: true,
  sort_order: 1,
};

const MOCK_SUBSCRIPTION = {
  id: "00000000-0000-4000-8000-0000000000f2",
  organization_id: MOCK_ORG_ID,
  plan_id: MOCK_PLAN.id,
  status: "active",
  billing_cycle: "monthly",
  current_period_start: "2026-10-01T00:00:00Z",
  current_period_end: "2026-11-01T00:00:00Z",
  cancel_at_period_end: false,
  created_at: "2026-01-01T00:00:00Z",
  plan: MOCK_PLAN,
};

const MOCK_USAGE = {
  plan_code: "starter",
  plan_name: "Starter",
  metrics: [
    {
      metric: "conversations",
      label: "Conversations",
      category: "metered",
      used: 0,
      limit: 100,
      unlimited: false,
      percent: 0,
      period: "monthly",
    },
  ],
  generated_at: "2026-10-17T00:00:00Z",
};

const EMPTY_LIST = { items: [], total: 0 };

export type MockOverrides = {
  /** Conversations returned by GET /api/conversations (default: none). */
  conversations?: unknown[];
};

/**
 * Answer /api requests from fixtures so Studio renders without a backend.
 * Requests whose pathname does not start with /api/ (Vite module URLs that
 * happen to contain "/api/") are passed through untouched. Mutations are
 * refused, so a test can never change data.
 */
export async function mockStudioApi(page: Page, overrides: MockOverrides = {}): Promise<void> {
  await page.route("**/api/**", (route) => answer(route, overrides));
}

function json(route: Route, status: number, body: unknown) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function answer(route: Route, overrides: MockOverrides): Promise<void> {
  const request = route.request();
  const url = new URL(request.url());
  if (!url.pathname.startsWith("/api/")) return route.continue();

  if (request.method() !== "GET") {
    return json(route, 405, { detail: "Mock API is read-only in end-to-end tests." });
  }

  const path = url.pathname.slice("/api".length);
  const widgetAnalytics = path.match(/^\/widgets\/([^/]+)\/analytics$/);
  const agentById = path.match(/^\/agents\/([^/]+)$/);

  if (path === "/auth/me") return json(route, 200, MOCK_ME);
  if (path === "/auth/identity") return json(route, 200, MOCK_IDENTITY);
  if (path === "/projects") return json(route, 200, { items: [MOCK_PROJECT], total: 1 });
  if (path === "/conversations") return json(route, 200, overrides.conversations ?? []);
  if (path === "/agents") return json(route, 200, EMPTY_LIST);
  if (agentById) return json(route, 200, { ...MOCK_AGENT, id: agentById[1] });
  if (path === "/widgets") return json(route, 200, { items: [MOCK_WIDGET], total: 1 });
  if (widgetAnalytics) {
    // No visit has reached the widget yet, so the install page waits for one.
    return json(route, 200, {
      widget_id: widgetAnalytics[1],
      status: "published",
      sessions: 0,
      by_event: {},
      last_loaded_at: null,
    });
  }
  if (path === "/billing/subscription") return json(route, 200, MOCK_SUBSCRIPTION);
  if (path === "/billing/plans") return json(route, 200, { items: [MOCK_PLAN], total: 1 });
  if (path === "/usage") return json(route, 200, MOCK_USAGE);
  if (path === "/leads") return json(route, 200, []);
  if (path === "/leads/stats") {
    return json(route, 200, {
      total: 0,
      new: 0,
      contacted: 0,
      qualified: 0,
      won: 0,
      lost: 0,
      hot: 0,
      warm: 0,
      cold: 0,
      conversion_rate: 0,
    });
  }
  if (path === "/team/members" || path === "/team/invitations") {
    return json(route, 200, EMPTY_LIST);
  }
  if (path === "/calls/campaigns") return json(route, 200, []);
  if (path === "/workflows")
    return json(route, 200, { items: [], total: 0, limit: 200, offset: 0 });

  return json(route, 404, { detail: "Not provided by the end-to-end mock." });
}

/** Fails if the page is wider than the viewport (a horizontal scrollbar). */
export async function expectNoHorizontalScroll(page: Page): Promise<void> {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "page must not scroll horizontally").toBeLessThanOrEqual(1);
}

/** Collects uncaught errors thrown by page scripts. Call before navigating. */
export function trackPageErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

/**
 * Wait until the page has loaded and React has attached to its controls.
 * The dev server compiles lazy route chunks on first visit, so the allowance
 * is longer than the shared helper's.
 */
export async function waitForHydration(page: Page): Promise<void> {
  await page.waitForLoadState("load");
  await page.waitForFunction(
    () =>
      Array.from(document.querySelectorAll("button, a, input")).some((el) =>
        Object.keys(el).some((key) => key.startsWith("__reactProps")),
      ),
    undefined,
    { timeout: 45_000 },
  );
}
