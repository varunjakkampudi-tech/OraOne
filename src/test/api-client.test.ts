import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiRequest, API_BASE } from "@/lib/api/client";
import { getMe, verifyEmailCode } from "@/lib/api/auth";

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function stubFetch(handler: (url: string, init: RequestInit) => Response | Promise<Response>) {
  const calls: { url: string; init: RequestInit }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init: init ?? {} });
    return handler(url, init ?? {});
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("API client", () => {
  it("uses same-origin /api unless a base URL is configured", () => {
    expect(API_BASE).toBe("/api");
  });

  it("sends session cookies and no bearer token", async () => {
    const calls = stubFetch(() => jsonResponse(200, { email: "a@example.com" }));
    await getMe();
    expect(calls[0]?.init.credentials).toBe("include");
    expect(new Headers(calls[0]?.init.headers).has("Authorization")).toBe(false);
  });

  it("surfaces FastAPI detail messages", async () => {
    stubFetch(() => jsonResponse(409, { detail: "Project name already exists." }));
    await expect(apiRequest("/projects", { method: "POST", body: {} })).rejects.toMatchObject({
      status: 409,
      message: "Project name already exists.",
    });
  });

  it("surfaces provider error messages from { error, message } bodies", async () => {
    stubFetch(() =>
      jsonResponse(502, { error: "auth", message: "Invalid AI provider credentials." }),
    );
    await expect(
      apiRequest("/conversations/x/messages", { method: "POST", body: {} }),
    ).rejects.toThrow("Invalid AI provider credentials.");
  });

  it("surfaces the message from the { success, error: { message } } envelope", async () => {
    stubFetch(() =>
      jsonResponse(503, {
        success: false,
        error: { code: "SERVICE_UNAVAILABLE", message: "This integration is not configured." },
        requestId: "req-1",
      }),
    );
    await expect(apiRequest("/integrations/connect", { method: "POST", body: {} })).rejects.toThrow(
      "This integration is not configured.",
    );
  });

  it("falls back to a generic message for server errors without a usable body", async () => {
    stubFetch(() => new Response("<html>oops</html>", { status: 500 }));
    await expect(apiRequest("/agents")).rejects.toThrow("OraOne couldn't complete that right now.");
  });

  it("reports unreachable API as status 0", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    const error = await apiRequest("/agents").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(0);
  });

  it("refreshes once after a 401 and retries the original request", async () => {
    let meCalls = 0;
    const calls = stubFetch((url) => {
      if (url.endsWith("/auth/refresh")) return jsonResponse(200, { access_token: "x" });
      meCalls += 1;
      return meCalls === 1
        ? jsonResponse(401, { detail: "expired" })
        : jsonResponse(200, { email: "a@example.com" });
    });
    await expect(getMe()).resolves.toMatchObject({ email: "a@example.com" });
    expect(calls.map((c) => c.url.replace(API_BASE, ""))).toEqual([
      "/auth/me",
      "/auth/refresh",
      "/auth/me",
    ]);
  });

  it("does not refresh when a code is rejected", async () => {
    const calls = stubFetch(() => jsonResponse(400, { detail: "Incorrect or expired code." }));
    await expect(verifyEmailCode({ email: "a@example.com", code: "000000" })).rejects.toThrow(
      "Incorrect or expired code.",
    );
    expect(calls).toHaveLength(1);
  });
});
