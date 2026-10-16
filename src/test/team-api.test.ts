import { afterEach, describe, expect, it, vi } from "vitest";
import { API_BASE } from "@/lib/api/client";
import {
  changeMemberRole,
  createInvitation,
  listInvitations,
  listMembers,
  removeMember,
  revokeInvitation,
} from "@/lib/api/team";

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

describe("team API", () => {
  it("lists members and invitations for the organization", async () => {
    const calls = stubFetch({ items: [], total: 0 });
    await listMembers();
    await listInvitations();
    expect(calls.map((c) => c.url)).toEqual([
      `${API_BASE}/team/members`,
      `${API_BASE}/team/invitations`,
    ]);
  });

  it("changes a member role with PATCH", async () => {
    const calls = stubFetch({ id: "m-1", role: "admin" });
    await changeMemberRole("m-1", "admin");
    expect(calls[0]?.url).toBe(`${API_BASE}/team/members/m-1`);
    expect(calls[0]?.init.method).toBe("PATCH");
    expect(calls[0]?.init.body).toBe(JSON.stringify({ role: "admin" }));
  });

  it("removes a member with DELETE", async () => {
    const calls = stubFetch({ ok: true });
    await removeMember("m-1");
    expect(calls[0]?.url).toBe(`${API_BASE}/team/members/m-1`);
    expect(calls[0]?.init.method).toBe("DELETE");
  });

  it("creates an invitation with an email and role", async () => {
    const calls = stubFetch({ invitation: {}, message: "sent" }, 201);
    await createInvitation({ email: "pat@example.com", role: "viewer" });
    expect(calls[0]?.url).toBe(`${API_BASE}/team/invitations`);
    expect(calls[0]?.init.body).toBe(JSON.stringify({ email: "pat@example.com", role: "viewer" }));
  });

  it("revokes an invitation with DELETE", async () => {
    const calls = stubFetch({ ok: true });
    await revokeInvitation("inv-1");
    expect(calls[0]?.url).toBe(`${API_BASE}/team/invitations/inv-1`);
    expect(calls[0]?.init.method).toBe("DELETE");
  });
});
