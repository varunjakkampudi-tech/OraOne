import { afterEach, describe, expect, it, vi } from "vitest";
import { API_BASE } from "@/lib/api/client";
import {
  createKnowledgeBase,
  deleteDocument,
  listDocuments,
  listKnowledgeBases,
  searchKnowledge,
  updateKnowledgeBaseStatus,
  uploadDocument,
} from "@/lib/api/knowledge";

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

describe("knowledge API", () => {
  it("lists knowledge bases for a workspace", async () => {
    const calls = stubFetch({ items: [], total: 0, limit: 100, offset: 0 });
    await listKnowledgeBases("ws-1");
    expect(calls[0]?.url).toBe(`${API_BASE}/knowledge-bases?limit=100&sort=name`);
    expect(new Headers(calls[0]?.init.headers).get("X-Project-Id")).toBe("ws-1");
  });

  it("creates a knowledge base in the workspace", async () => {
    const calls = stubFetch({ id: "kb-1" }, 201);
    await createKnowledgeBase("ws-1", { name: "Help center" });
    expect(calls[0]?.init.method).toBe("POST");
    expect(calls[0]?.init.body).toBe(JSON.stringify({ name: "Help center" }));
    expect(new Headers(calls[0]?.init.headers).get("X-Project-Id")).toBe("ws-1");
  });

  it("filters documents by knowledge base", async () => {
    const calls = stubFetch({ items: [], total: 0, limit: 100, offset: 0 });
    await listDocuments("kb-9");
    expect(calls[0]?.url).toBe(`${API_BASE}/documents?knowledge_base_id=kb-9&limit=100`);
  });

  it("uploads a file as multipart form data without a JSON content type", async () => {
    const calls = stubFetch({ id: "doc-1" }, 201);
    const file = new File(["hello"], "faq.txt", { type: "text/plain" });
    await uploadDocument("kb-9", file);
    expect(calls[0]?.url).toBe(`${API_BASE}/documents/upload`);
    expect(calls[0]?.init.method).toBe("POST");
    const form = calls[0]?.init.body as FormData;
    expect(form).toBeInstanceOf(FormData);
    expect(form.get("knowledge_base_id")).toBe("kb-9");
    expect((form.get("file") as File).name).toBe("faq.txt");
    expect(new Headers(calls[0]?.init.headers).get("Content-Type")).toBeNull();
  });

  it("deletes a document by id", async () => {
    const calls = stubFetch(undefined, 204);
    await expect(deleteDocument("doc-1")).resolves.toBeUndefined();
    expect(calls[0]?.url).toBe(`${API_BASE}/documents/doc-1`);
    expect(calls[0]?.init.method).toBe("DELETE");
  });

  it("searches knowledge, omitting the knowledge base when none is chosen", async () => {
    const calls = stubFetch({ query: "refund", hits: [] });
    await searchKnowledge("refund", undefined, 5);
    expect(calls[0]?.url).toBe(`${API_BASE}/knowledge/search`);
    expect(calls[0]?.init.body).toBe(JSON.stringify({ query: "refund", top_k: 5 }));
  });

  it("sends the knowledge base filter with a search when one is chosen", async () => {
    const calls = stubFetch({ query: "refund", hits: [] });
    await searchKnowledge("refund", "kb-9");
    expect(JSON.parse(String(calls[0]?.init.body))).toEqual({
      query: "refund",
      knowledge_base_id: "kb-9",
      top_k: 8,
    });
  });
});

describe("knowledge base status", () => {
  it("changes a knowledge base's status with PUT", async () => {
    const calls = stubFetch({ id: "kb-9", status: "active" });
    await updateKnowledgeBaseStatus("kb-9", "active");
    expect(calls[0]?.url).toBe(`${API_BASE}/knowledge-bases/kb-9`);
    expect(calls[0]?.init.method).toBe("PUT");
    expect(calls[0]?.init.body).toBe(JSON.stringify({ status: "active" }));
  });
});
