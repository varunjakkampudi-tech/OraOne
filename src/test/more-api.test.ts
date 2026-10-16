import { afterEach, describe, expect, it, vi } from "vitest";
import { API_BASE } from "@/lib/api/client";
import { createApiKey, deleteApiKey, listApiKeys } from "@/lib/api/api-keys";
import { getAnalyticsOverview } from "@/lib/api/analytics";
import { updateProfileName } from "@/lib/api/account";

function stubFetch(body: unknown = {}) {
  const calls: { url: string; init: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), init: init ?? {} });
      return new Response(body === undefined ? null : JSON.stringify(body), {
        status: body === undefined ? 204 : 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return calls;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API key calls", () => {
  it("lists keys for one workspace", async () => {
    const calls = stubFetch({ keys: [], scopes: [] });
    await listApiKeys("ws-1");
    expect(calls[0]?.url).toBe(`${API_BASE}/api-keys`);
    expect(new Headers(calls[0]?.init.headers).get("X-Project-Id")).toBe("ws-1");
  });

  it("creates a key with the chosen scopes", async () => {
    const calls = stubFetch({ key: "ork_x", api_key: {} });
    await createApiKey("ws-1", { name: "Site", scopes: ["chat:read"] });
    expect(calls[0]?.init.method).toBe("POST");
    expect(calls[0]?.init.body).toBe(JSON.stringify({ name: "Site", scopes: ["chat:read"] }));
  });

  it("deletes a key by id", async () => {
    const calls = stubFetch(undefined);
    await deleteApiKey("key-7");
    expect(calls[0]?.url).toBe(`${API_BASE}/api-keys/key-7`);
    expect(calls[0]?.init.method).toBe("DELETE");
  });
});

describe("analytics and account calls", () => {
  it("requests the overview for a period", async () => {
    const calls = stubFetch({});
    await getAnalyticsOverview("ws-1", 7);
    expect(calls[0]?.url).toBe(`${API_BASE}/analytics/overview?days=7`);
  });

  it("updates the display name with PATCH", async () => {
    const calls = stubFetch({ name: "Ada" });
    await updateProfileName("Ada");
    expect(calls[0]?.url).toBe(`${API_BASE}/auth/profile`);
    expect(calls[0]?.init.method).toBe("PATCH");
    expect(calls[0]?.init.body).toBe(JSON.stringify({ full_name: "Ada" }));
  });
});
