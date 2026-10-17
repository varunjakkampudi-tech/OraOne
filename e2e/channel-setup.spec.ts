import type { Route } from "@playwright/test";
import { expect, test } from "./fixtures";
import {
  expectNoHorizontalScroll,
  waitForHydration,
  MOCK_AGENT_ID,
  mockStudioApi,
  trackPageErrors,
} from "./product-support";

// WhatsApp setup at phone width. Every /api request is answered here or by the shared mock, so
// no backend, account or provider is reached. The channel rows are kept in memory for the test
// and the PATCH body is recorded, so the test can check what the form sent.

type Row = {
  channel: string;
  label: string;
  description: string;
  icon: string;
  enabled: boolean;
  status: string;
  embeddable: boolean;
  phone_number: string | null;
  provider: string | null;
  configuration: Record<string, string>;
  masked_secrets: Record<string, string>;
};

function row(channel: string, label: string): Row {
  return {
    channel,
    label,
    description: "",
    icon: "",
    enabled: false,
    status: "disabled",
    embeddable: false,
    phone_number: null,
    provider: null,
    configuration: {},
    masked_secrets: {},
  };
}

test.describe("WhatsApp channel settings", () => {
  test("saves the WhatsApp phone number ID through the API and the checklist reflects it", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "390", "Phone width (390px) only.");
    await mockStudioApi(page);
    const errors = trackPageErrors(page);

    const rows: Row[] = [row("chat", "Website Chat"), row("whatsapp", "WhatsApp")];
    const patches: unknown[] = [];

    // Registered after the shared mock, so these handlers answer first.
    await page.route(
      (url) => url.pathname === "/api/agents",
      (route) =>
        json(route, 200, { items: [{ id: MOCK_AGENT_ID, name: "Mock Assistant" }], total: 1 }),
    );
    await page.route(
      (url) => url.pathname.startsWith(`/api/agents/${MOCK_AGENT_ID}/channels`),
      async (route) => {
        const request = route.request();
        const path = new URL(request.url()).pathname;
        if (request.method() === "GET" && path === `/api/agents/${MOCK_AGENT_ID}/channels`) {
          return json(route, 200, {
            agent_id: MOCK_AGENT_ID,
            agent_name: "Mock Assistant",
            items: rows,
          });
        }
        if (
          request.method() === "PATCH" &&
          path === `/api/agents/${MOCK_AGENT_ID}/channels/whatsapp`
        ) {
          const body = request.postDataJSON() as {
            enabled?: boolean;
            settings?: { phone_number_id?: string | null };
          };
          patches.push(body);
          const target = rows.find((item) => item.channel === "whatsapp");
          if (!target) return json(route, 404, { detail: "Unknown channel" });
          if (typeof body.enabled === "boolean") {
            target.enabled = body.enabled;
            target.status = body.enabled ? "active" : "disabled";
          }
          if (body.settings && "phone_number_id" in body.settings) {
            target.configuration = body.settings.phone_number_id
              ? { phone_number_id: body.settings.phone_number_id }
              : {};
          }
          return json(route, 200, target);
        }
        return json(route, 405, { detail: "Not part of this test." });
      },
    );

    await page.goto("/studio/channels/whatsapp");
    await waitForHydration(page);

    await expect(
      page.getByRole("heading", { level: 2, name: "Connection settings" }),
    ).toBeVisible();
    const phoneId = page.getByLabel("Phone number ID", { exact: true });
    await expect(phoneId).toBeVisible();
    await expectNoHorizontalScroll(page);

    // Invalid input is explained in the form and nothing is sent.
    await phoneId.fill("+1 415 555 0123");
    await page.getByRole("button", { name: "Save settings" }).click();
    await expect(page.getByRole("alert").filter({ hasText: "digits only" })).toBeVisible();
    expect(patches, "no request for invalid input").toEqual([]);

    // Valid input with the switch on is saved through the API.
    await phoneId.fill("100200300400500");
    await page.getByRole("switch", { name: "Turn on WhatsApp for this assistant" }).click();
    await page.getByRole("button", { name: "Save settings" }).click();

    await expect(page.getByRole("status").filter({ hasText: "Saved." })).toBeVisible();
    expect(patches).toEqual([{ enabled: true, settings: { phone_number_id: "100200300400500" } }]);

    // The checklist reads the saved state from the reloaded channel rows.
    await expect(page.getByText("Phone number ID is saved.", { exact: true })).toBeVisible();
    await expect(page.getByText("WhatsApp is connected.", { exact: true })).toBeVisible();
    await expectNoHorizontalScroll(page);
    expect(errors, "no uncaught page errors").toEqual([]);
  });
});

function json(route: Route, status: number, body: unknown) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}
