import { apiRequest } from "./client";

// Knowledge bases are scoped to a workspace (project). Documents are scoped to
// the organization and filtered by knowledge base. Search runs over processed
// documents only, so newly uploaded files become searchable after processing.

export type KnowledgeBase = {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  status: string;
  document_count: number;
  created_at: string;
  updated_at: string;
};

export type KnowledgeBaseList = {
  items: KnowledgeBase[];
  total: number;
  limit: number;
  offset: number;
};

export type DocumentStatus = "pending" | "processing" | "processed" | "failed";

export type DocumentRecord = {
  id: string;
  knowledge_base_id: string;
  organization_id: string;
  filename: string;
  file_type: string | null;
  file_size: number | null;
  status: DocumentStatus | string;
  chunk_count: number;
  embedded_count: number;
  processing_error: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentList = {
  items: DocumentRecord[];
  total: number;
  limit: number;
  offset: number;
};

export type KnowledgeHit = {
  document_id: string | null;
  website_page_id: string | null;
  document: string;
  url: string | null;
  source_type: string;
  content: string;
  page: number | null;
  section: string | null;
  score: number | null;
};

export type KnowledgeSearchResponse = {
  query: string;
  hits: KnowledgeHit[];
};

export function listKnowledgeBases(projectId: string) {
  return apiRequest<KnowledgeBaseList>("/knowledge-bases?limit=100&sort=name", { projectId });
}

export function createKnowledgeBase(projectId: string, input: { name: string }) {
  return apiRequest<KnowledgeBase>("/knowledge-bases", {
    method: "POST",
    body: input,
    projectId,
  });
}

export function listDocuments(knowledgeBaseId: string, limit = 100) {
  const params = new URLSearchParams({
    knowledge_base_id: knowledgeBaseId,
    limit: String(limit),
  });
  return apiRequest<DocumentList>(`/documents?${params.toString()}`);
}

export function uploadDocument(knowledgeBaseId: string, file: File) {
  const form = new FormData();
  form.append("knowledge_base_id", knowledgeBaseId);
  form.append("file", file);
  return apiRequest<DocumentRecord>("/documents/upload", { method: "POST", body: form });
}

export function deleteDocument(documentId: string) {
  return apiRequest<void>(`/documents/${documentId}`, { method: "DELETE" });
}

export function searchKnowledge(query: string, knowledgeBaseId?: string, topK = 8) {
  return apiRequest<KnowledgeSearchResponse>("/knowledge/search", {
    method: "POST",
    body: { query, knowledge_base_id: knowledgeBaseId, top_k: topK },
  });
}

export const KNOWLEDGE_BASE_STATUSES = ["draft", "active", "archived"] as const;
export type KnowledgeBaseStatusValue = (typeof KNOWLEDGE_BASE_STATUSES)[number];

/** Only `active` knowledge bases answer assistants and search. */
export function updateKnowledgeBaseStatus(
  knowledgeBaseId: string,
  status: KnowledgeBaseStatusValue,
) {
  return apiRequest<KnowledgeBase>(`/knowledge-bases/${knowledgeBaseId}`, {
    method: "PUT",
    body: { status },
  });
}
