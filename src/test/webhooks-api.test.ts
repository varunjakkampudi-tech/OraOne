import { afterEach, describe, expect, it, vi } from "vitest";
import { API_BASE } from "@/lib/api/client";
import {
  createWebhook,
  deleteWebhook,
  listWebhookDeliveries,
  listWebhooks,
  rotateWebhookSecret,
  testWebhook,
  updateWebhook,
} from "@/lib/api/webhooks";

function stubFetch(body: unknown = {}, status = 200) {
  const calls: { url: string; init: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), init: init ?? {} });
      return new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return calls;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("webhooks API", () => {
  it("lists endpoints and the event catalogue for a workspace", async () => {
    const calls = stubFetch({ webhooks: [], events: [] });
    await listWebhooks("ws-1");
    expect(calls[0]?.url).toBe(`${API_BASE}/webhooks`);
    expect(new Headers(calls[0]?.init.headers).get("X-Project-Id")).toBe("ws-1");
  });

  it("creates an endpoint with its selected events", async () => {
    const calls = stubFetch({ webhook: {}, secret: "whsec_x" }, 201);
    await createWebhook("ws-1", { url: "https://example.com/hook", events: ["document.uploaded"] });
    expect(calls[0]?.init.method).toBe("POST");
    expect(JSON.parse(String(calls[0]?.init.body))).toEqual({
      url: "https://example.com/hook",
      events: ["document.uploaded"],
    });
  });

  it("pauses an endpoint with PATCH", async () => {
    const calls = stubFetch({ id: "wh-1", status: "paused" });
    await updateWebhook("wh-1", { status: "paused" });
    expect(calls[0]?.url).toBe(`${API_BASE}/webhooks/wh-1`);
    expect(calls[0]?.init.method).toBe("PATCH");
    expect(calls[0]?.init.body).toBe(JSON.stringify({ status: "paused" }));
  });

  it("deletes, rotates, and tests an endpoint", async () => {
    const calls = stubFetch({ secret: "whsec_y" });
    await deleteWebhook("wh-1");
    await rotateWebhookSecret("wh-1");
    await testWebhook("wh-1");
    expect(calls.map((c) => [c.init.method, c.url])).toEqual([
      ["DELETE", `${API_BASE}/webhooks/wh-1`],
      ["POST", `${API_BASE}/webhooks/wh-1/rotate`],
      ["POST", `${API_BASE}/webhooks/wh-1/test`],
    ]);
  });

  it("reads recent deliveries with a limit", async () => {
    const calls = stubFetch([]);
    await listWebhookDeliveries("wh-1", 5);
    expect(calls[0]?.url).toBe(`${API_BASE}/webhooks/wh-1/deliveries?limit=5`);
  });
});
