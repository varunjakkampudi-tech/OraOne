import { afterEach, describe, expect, it, vi } from "vitest";
import { API_BASE } from "@/lib/api/client";
import {
  connectIntegration,
  disconnectIntegration,
  listIntegrations,
  syncIntegration,
} from "@/lib/api/integrations";

function stubFetch(body: unknown = {}, status = 200) {
  const calls: { url: string; init: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), init: init ?? {} });
      if (status === 204) return new Response(null, { status });
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

describe("integrations API", () => {
  it("lists the catalog for a workspace", async () => {
    const calls = stubFetch({ items: [], total: 0 });
    await listIntegrations("ws-1");
    expect(calls[0]?.url).toBe(`${API_BASE}/integrations`);
    expect(new Headers(calls[0]?.init.headers).get("X-Project-Id")).toBe("ws-1");
  });

  it("starts a connection by provider without requesting mock mode", async () => {
    const calls = stubFetch({ integration: null, authorize_url: "https://accounts.example/auth" });
    const result = await connectIntegration("ws-1", "google_drive");
    expect(result.authorize_url).toBe("https://accounts.example/auth");
    expect(calls[0]?.url).toBe(`${API_BASE}/integrations/connect`);
    expect(calls[0]?.init.body).toBe(JSON.stringify({ provider: "google_drive" }));
  });

  it("triggers a sync for one integration", async () => {
    const calls = stubFetch({ id: "job-1" }, 202);
    await syncIntegration("ws-1", "int-1");
    expect(calls[0]?.url).toBe(`${API_BASE}/integrations/int-1/sync`);
    expect(calls[0]?.init.method).toBe("POST");
  });

  it("disconnects an integration with DELETE", async () => {
    const calls = stubFetch({ ok: true });
    await disconnectIntegration("ws-1", "int-1");
    expect(calls[0]?.url).toBe(`${API_BASE}/integrations/int-1`);
    expect(calls[0]?.init.method).toBe("DELETE");
  });
});
