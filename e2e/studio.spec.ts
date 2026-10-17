import type { Locator } from "@playwright/test";
import { expect, test } from "./fixtures";
import {
  expectNoHorizontalScroll,
  waitForHydration,
  MOCK_CONVERSATION_ID,
  MOCK_AGENT_ID,
  mockStudioApi,
  trackPageErrors,
} from "./product-support";

// Signed-in Studio pages. Every /api request is answered by the mock in
// e2e/product-support.ts, so no real account, session or backend data is used.

// OraOne OS hub at /studio and the four channel setup pages. The mock has no assistant by default,
// so every channel reads "Not connected yet"; the connected case overrides only the two reads it needs.
const HUB_AREAS = [
  "Website chat",
  "AI Voice",
  "WhatsApp",
  "Instagram",
  "Omnichannel inbox",
  "AI Studio",
  "Marketing",
  "Marketplace",
  "Integrations",
  "Calls",
];

test.describe("OraOne OS hub and channel setup", () => {
  test.beforeEach(async ({ page }) => {
    await mockStudioApi(page);
  });

  test("/studio shows the hub with one card per product area and no horizontal scroll", async ({
    page,
  }) => {
    const errors = trackPageErrors(page);

    await page.goto("/studio");
    await waitForHydration(page);

    await expect(page.getByRole("heading", { level: 1, name: "OraOne OS" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Product areas" })).toBeVisible();
    for (const name of HUB_AREAS) {
      await expect(page.getByRole("heading", { level: 3, name, exact: true })).toBeVisible();
    }
    await expectNoHorizontalScroll(page);
    expect(errors, "no uncaught page errors").toEqual([]);
  });

  test("hub reports Not connected yet for channels when there is no assistant", async ({
    page,
  }) => {
    await page.goto("/studio");
    await waitForHydration(page);

    const whatsapp = page.getByRole("article").filter({ hasText: "WhatsApp" }).first();
    await expect(whatsapp.getByText("Not connected yet", { exact: true })).toBeVisible();
    await expect(whatsapp.getByRole("link", { name: "Set up WhatsApp" })).toHaveAttribute(
      "href",
      "/studio/channels/whatsapp",
    );
    await expect(page.getByText("Live", { exact: true })).toHaveCount(0);
  });

  test("hub shows Connected for website chat when the chat channel is active", async ({ page }) => {
    await page.route(
      (url) => url.pathname === "/api/agents",
      (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [
              {
                id: MOCK_AGENT_ID,
                name: "Mock Assistant",
                description: "Customer support",
                system_prompt: null,
              },
            ],
            total: 1,
          }),
        }),
    );
    await page.route(
      (url) => url.pathname === `/api/agents/${MOCK_AGENT_ID}/channels`,
      (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            agent_id: MOCK_AGENT_ID,
            agent_name: "Mock Assistant",
            items: [
              { channel: "chat", enabled: true, status: "active", label: "Website Chat" },
              { channel: "widget", enabled: true, status: "active", label: "Website Widget" },
            ],
          }),
        }),
    );

    await page.goto("/studio");
    await waitForHydration(page);

    const website = page.getByRole("article").filter({ hasText: "Website chat" }).first();
    await expect(website.getByText("Connected", { exact: true })).toBeVisible();
    await expect(website.getByRole("link", { name: "Open Website chat" })).toBeVisible();
    // Channels the API does not report stay not connected.
    const voice = page.getByRole("article").filter({ hasText: "AI Voice" }).first();
    await expect(voice.getByText("Not connected yet", { exact: true })).toBeVisible();
  });

  test("the navigation shows the four groups and keeps every studio route reachable", async ({
    page,
  }) => {
    await page.goto("/studio");
    await waitForHydration(page);

    const width = page.viewportSize()?.width ?? 1280;
    let nav: Locator;
    if (width < 768) {
      await page.getByRole("button", { name: "Menu" }).click();
      nav = page.getByRole("navigation", { name: "All studio sections" });
    } else {
      nav = page.getByRole("navigation", { name: "Studio sections" });
    }

    for (const group of ["Conversations", "Channels", "Grow", "Build"]) {
      await expect(nav.getByRole("region", { name: group })).toBeVisible();
    }
    await expect(nav.getByRole("link", { name: "WhatsApp" })).toHaveAttribute(
      "href",
      "/studio/channels/whatsapp",
    );
    await expect(nav.getByRole("link", { name: "AI Studio" })).toHaveAttribute(
      "href",
      "/studio/assistants",
    );
    await expect(nav.getByRole("link", { name: "Settings" })).toHaveAttribute(
      "href",
      "/studio/account",
    );
    await expectNoHorizontalScroll(page);
  });

  for (const channel of ["website-chat", "whatsapp", "instagram", "voice"]) {
    test(`/studio/channels/${channel} shows its checklist without horizontal scroll`, async ({
      page,
    }) => {
      const errors = trackPageErrors(page);

      await page.goto(`/studio/channels/${channel}`);
      await waitForHydration(page);

      await expect(page.getByRole("heading", { level: 2, name: "What you need" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "What is done" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "What is next" })).toBeVisible();
      await expectNoHorizontalScroll(page);
      expect(errors, "no uncaught page errors").toEqual([]);
    });
  }

  test("an unknown channel name shows a plain message instead of a blank page", async ({
    page,
  }) => {
    await page.goto("/studio/channels/fax");
    await waitForHydration(page);

    await expect(page.getByText("This setup page doesn't exist.")).toBeVisible();
    await expectNoHorizontalScroll(page);
  });
});

test.describe("studio with mocked API", () => {
  test.beforeEach(async ({ page }) => {
    await mockStudioApi(page);
  });

  const PAGES: Array<{ path: string; heading: string }> = [
    { path: "/studio/assistants", heading: "Your assistants" },
    { path: "/studio/inbox", heading: "Conversations" },
    { path: "/studio/leads", heading: "Leads" },
    { path: "/studio/team", heading: "Team" },
    { path: "/studio/billing", heading: "Billing" },
    { path: "/studio/calls", heading: "Calls" },
    { path: "/studio/workflows", heading: "Workflows" },
  ];

  for (const entry of PAGES) {
    test(`${entry.path} renders its main heading without horizontal scroll`, async ({ page }) => {
      const errors = trackPageErrors(page);

      await page.goto(entry.path);
      await waitForHydration(page);

      await expect(page.getByRole("heading", { level: 1, name: entry.heading })).toBeVisible();
      await expectNoHorizontalScroll(page);
      expect(errors, "no uncaught page errors").toEqual([]);
    });
  }

  test("inbox offers the channel filter", async ({ page }) => {
    // The filter is only rendered once there is at least one conversation,
    // so this test returns one fake conversation from the mock.
    await page.unroute("**/api/**");
    await mockStudioApi(page, {
      conversations: [
        {
          id: MOCK_CONVERSATION_ID,
          agent_id: MOCK_AGENT_ID,
          channel: "chat",
          title: "Mock visitor question",
          status: "open",
          created_at: "2026-10-01T00:00:00Z",
          updated_at: "2026-10-01T00:00:00Z",
          last_message_at: "2026-10-01T00:00:00Z",
          is_archived: false,
        },
      ],
    });

    await page.goto("/studio/inbox");
    await waitForHydration(page);

    const filter = page.getByLabel("Filter by channel");
    await expect(filter).toBeVisible();
    await expect(filter).toHaveValue("");
    await expect(page.getByRole("option", { name: "All channels" })).toBeAttached();
  });

  test("calls page shows its empty state", async ({ page }) => {
    await page.goto("/studio/calls");
    await waitForHydration(page);

    await expect(page.getByText("No call campaigns yet.")).toBeVisible();
    // The page header and the empty state both offer this action; check the one in the empty state.
    await expect(
      page
        .getByRole("region", { name: "Campaigns" })
        .getByRole("button", { name: "Create campaign from imported leads" }),
    ).toBeVisible();
  });
});
