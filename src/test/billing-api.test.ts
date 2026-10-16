import { afterEach, describe, expect, it, vi } from "vitest";
import { API_BASE } from "@/lib/api/client";
import { getSubscription, getUsage, listPlans } from "@/lib/api/billing";

function stubFetch(body: unknown = {}) {
  const calls: { url: string; init: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      calls.push({ url: String(input), init: init ?? {} });
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return calls;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("billing API", () => {
  it("reads plans, the subscription, and usage without writing anything", async () => {
    const calls = stubFetch({});
    await listPlans();
    await getSubscription();
    await getUsage();
    expect(calls.map((c) => c.url)).toEqual([
      `${API_BASE}/billing/plans`,
      `${API_BASE}/billing/subscription`,
      `${API_BASE}/usage`,
    ]);
    expect(calls.every((c) => (c.init.method ?? "GET") === "GET")).toBe(true);
  });
});
