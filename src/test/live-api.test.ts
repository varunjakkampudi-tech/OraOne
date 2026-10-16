import { afterEach, describe, expect, it, vi } from "vitest";
import { API_BASE } from "@/lib/api/client";
import { listLeads, updateLeadStatus } from "@/lib/api/leads";
import { listConversations, listMessages } from "@/lib/api/inbox";

function stubFetch(body: unknown = []) {
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

describe("live API calls", () => {
  it("scopes lead lists to the workspace and filters by status", async () => {
    const calls = stubFetch([]);
    await listLeads("ws-1", "won");
    expect(calls[0]?.url).toBe(`${API_BASE}/leads?limit=200&sort=-created_at&status=won`);
    expect(new Headers(calls[0]?.init.headers).get("X-Project-Id")).toBe("ws-1");
  });

  it("omits the status filter when showing all leads", async () => {
    const calls = stubFetch([]);
    await listLeads("ws-1");
    expect(calls[0]?.url).not.toContain("status=");
  });

  it("updates one lead's status with PATCH", async () => {
    const calls = stubFetch({ id: "lead-1", status: "qualified" });
    await updateLeadStatus("ws-1", "lead-1", "qualified");
    expect(calls[0]?.url).toBe(`${API_BASE}/leads/lead-1`);
    expect(calls[0]?.init.method).toBe("PATCH");
    expect(calls[0]?.init.body).toBe(JSON.stringify({ status: "qualified" }));
  });

  it("requests recent conversations for the inbox", async () => {
    const calls = stubFetch([]);
    await listConversations(50);
    expect(calls[0]?.url).toBe(`${API_BASE}/conversations?limit=50&sort=recent`);
  });

  it("requests the messages of one conversation", async () => {
    const calls = stubFetch([]);
    await listMessages("conv-9");
    expect(calls[0]?.url).toBe(`${API_BASE}/conversations/conv-9/messages?limit=500`);
  });
});
