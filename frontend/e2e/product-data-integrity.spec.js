const { test, expect } = require("@playwright/test");

const user = {
  id: "data-integrity-user",
  userId: "data-integrity-user",
  email: "data-integrity@example.test",
  name: "Data Integrity User",
  full_name: "Data Integrity User",
  role: "user",
  platform_role: "user",
  plan: "free",
  status: "active",
};

const identity = {
  user,
  organization: {
    id: "data-integrity-org",
    name: "Data Integrity Workspace",
    slug: "data-integrity-workspace",
    plan: "free",
  },
  membership: {
    organization_id: "data-integrity-org",
    role: "owner",
    status: "active",
  },
  is_new_user: false,
};

function makeLead(index, createdAt) {
  return {
    id: `lead-${index}`,
    name: `Lead ${index}`,
    email: `lead-${index}@example.test`,
    phone: `+100000000${index}`,
    source: "website",
    intent: "support",
    status: "New",
    score: 50,
    ...(createdAt ? { created_at: createdAt } : {}),
  };
}

async function installApiFixture(
  page,
  { analyticsStatus = 200, leads = [], conversations = [] } = {},
) {
  await page.addInitScript(
    ({ authIdentity }) => {
      localStorage.setItem("oraone_access_token", "data-integrity-token");
      localStorage.setItem("oraone_identity", JSON.stringify(authIdentity));
      localStorage.setItem("oraone_tour_seen_v1", "1");
    },
    { authIdentity: identity },
  );

  await page.route("**/api/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    let status = 200;
    let body = {};

    if (pathname.endsWith("/auth/me")) {
      body = user;
    } else if (pathname.endsWith("/auth/identity")) {
      body = identity;
    } else if (pathname.endsWith("/entitlements/me")) {
      body = { products: {}, features: {}, statuses: {}, catalog: [] };
    } else if (pathname.endsWith("/projects")) {
      body = { items: [] };
    } else if (pathname.endsWith("/branding")) {
      body = {};
    } else if (pathname.includes("/analytics/")) {
      status = analyticsStatus;
      body =
        status === 200
          ? { totals: {}, series: {}, breakdowns: {} }
          : { detail: "fixture failure" };
    } else if (pathname.endsWith("/v2/conversations")) {
      const query = new URL(route.request().url()).searchParams;
      const offset = Number(query.get("offset") || 0);
      body = conversations.slice(
        offset,
        offset + Number(query.get("limit") || 100),
      );
    } else if (pathname.endsWith("/messages")) {
      body = [];
    } else if (pathname.endsWith("/leads/stats")) {
      body = { total: leads.length };
    } else if (pathname.endsWith("/leads")) {
      body = leads;
    }

    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

test("analytics API failure is unavailable and retryable, not zero-filled", async ({
  page,
}) => {
  test.setTimeout(60_000);
  await installApiFixture(page, { analyticsStatus: 500 });
  await page.goto("/app/analytics");
  await expect(
    page.getByRole("heading", { name: "Analytics", exact: true }),
  ).toBeVisible({ timeout: 30_000 });

  await expect(page.getByText("Analytics unavailable")).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  await expect(page.getByText("Total Conversations")).toHaveCount(0);
});

test("inbox loads conversations beyond the backend's first batch", async ({
  page,
}) => {
  await installApiFixture(page, {
    conversations: Array.from({ length: 101 }, (_, i) => ({
      id: `conversation-${i + 1}`,
      customer_name: `Contact ${i + 1}`,
      status: "active",
      channel: "chat",
    })),
  });
  await page.goto("/app/conversations");
  await expect(
    page.getByRole("button", { name: "Load more conversations" }),
  ).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Load more conversations" }).click();
  await expect(page.getByText("Contact 101", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Load more conversations" }),
  ).toHaveCount(0);
});

test("leads pagination reflects the loaded record count and unknown dates stay unknown", async ({
  page,
}) => {
  const leads = [
    makeLead(1),
    ...Array.from({ length: 10 }, (_, i) =>
      makeLead(i + 2, "2026-01-01T00:00:00Z"),
    ),
  ];
  await installApiFixture(page, { leads });
  await page.goto("/app/leads");

  await expect(page.getByText("Lead 1", { exact: true })).toBeVisible();
  await expect(
    page.locator("tbody tr").first().locator("td").nth(6),
  ).toHaveText("—");
  await expect(
    page.getByRole("button", { name: "2", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "3", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "5", exact: true }),
  ).toHaveCount(0);
});
