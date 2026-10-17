import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { Loader2, Plus, RefreshCw, Search, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { messageOf } from "@/lib/api/client";
import {
  KNOWLEDGE_BASE_STATUSES,
  createKnowledgeBase,
  deleteDocument,
  listDocuments,
  listKnowledgeBases,
  searchKnowledge,
  updateKnowledgeBaseStatus,
  uploadDocument,
  type DocumentRecord,
  type KnowledgeBase,
  type KnowledgeBaseStatusValue,
  type KnowledgeHit,
} from "@/lib/api/knowledge";
import { Loading, Notice } from "./studio-ui";
import { when, useWorkspaceId } from "@/lib/studio-helpers";
import { StudioFrame } from "./studio";

// Live knowledge screen under /studio. Documents are listed per knowledge base;
// only processed documents answer search. Failures are shown as they are.

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  processing: "Processing",
  processed: "Ready",
  failed: "Failed",
};

const MAX_UPLOAD_MB = 25;

export function KnowledgePage() {
  const workspace = useWorkspaceId();
  const [bases, setBases] = useState<KnowledgeBase[] | null>(null);
  const [basesError, setBasesError] = useState("");
  const [basesKey, setBasesKey] = useState(0);
  const [kbId, setKbId] = useState("");
  const [docs, setDocs] = useState<DocumentRecord[] | null>(null);
  const [docsTotal, setDocsTotal] = useState(0);
  const [docsError, setDocsError] = useState("");
  const [docsKey, setDocsKey] = useState(0);

  const [statusSaving, setStatusSaving] = useState(false);
  const [statusError, setStatusError] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState("");

  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [hits, setHits] = useState<{ query: string; items: KnowledgeHit[] } | null>(null);

  // Knowledge bases belong to the workspace; pick the first one by default.
  useEffect(() => {
    if (!workspace.id) return;
    let cancelled = false;
    setBasesError("");
    listKnowledgeBases(workspace.id)
      .then(({ items }) => {
        if (cancelled) return;
        setBases(items);
        setKbId((current) =>
          items.some((b) => b.id === current) ? current : (items[0]?.id ?? ""),
        );
      })
      .catch((err) => {
        if (!cancelled) setBasesError(messageOf(err, "Couldn't load knowledge bases."));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, basesKey]);

  // Documents are loaded for the selected knowledge base only.
  useEffect(() => {
    if (!kbId) return;
    let cancelled = false;
    setDocsError("");
    listDocuments(kbId)
      .then((res) => {
        if (cancelled) return;
        setDocs(res.items);
        setDocsTotal(res.total);
      })
      .catch((err) => {
        if (!cancelled) setDocsError(messageOf(err, "Couldn't load documents."));
      });
    return () => {
      cancelled = true;
    };
  }, [kbId, docsKey]);

  function selectBase(id: string) {
    setKbId(id);
    setDocs(null);
    setDocsError("");
    setConfirmId(null);
    setHits(null);
    setSearchError("");
  }

  async function changeStatus(status: KnowledgeBaseStatusValue) {
    if (!selected || status === selected.status) return;
    setStatusSaving(true);
    setStatusError("");
    try {
      const updated = await updateKnowledgeBaseStatus(selected.id, status);
      setBases(
        (rows) =>
          rows?.map((b) => (b.id === updated.id ? { ...b, status: updated.status } : b)) ?? rows,
      );
    } catch (err) {
      setStatusError(messageOf(err, "Couldn't change this knowledge base's status."));
    } finally {
      setStatusSaving(false);
    }
  }

  async function createBase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newName.trim();
    if (!workspace.id || !name) return;
    setCreating(true);
    setCreateError("");
    try {
      const base = await createKnowledgeBase(workspace.id, { name });
      setNewName("");
      setShowCreate(false);
      setBases((rows) => [...(rows ?? []), base]);
      selectBase(base.id);
    } catch (err) {
      setCreateError(messageOf(err, "Couldn't create this knowledge base."));
    } finally {
      setCreating(false);
    }
  }

  async function uploadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !kbId) return;
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setUploadError(`${file.name} is larger than ${MAX_UPLOAD_MB} MB.`);
      return;
    }
    setUploading(true);
    setUploadError("");
    try {
      const doc = await uploadDocument(kbId, file);
      setDocs((rows) => [doc, ...(rows ?? [])]);
      setDocsTotal((n) => n + 1);
      setBasesKey((k) => k + 1);
    } catch (err) {
      setUploadError(messageOf(err, "Couldn't upload this file."));
    } finally {
      setUploading(false);
    }
  }

  async function removeDocument(doc: DocumentRecord) {
    setDeletingId(doc.id);
    setDeleteError("");
    try {
      await deleteDocument(doc.id);
      setDocs((rows) => rows?.filter((r) => r.id !== doc.id) ?? rows);
      setDocsTotal((n) => Math.max(0, n - 1));
      setConfirmId(null);
      setBasesKey((k) => k + 1);
    } catch (err) {
      setDeleteError(messageOf(err, "Couldn't delete this document."));
    } finally {
      setDeletingId(null);
    }
  }

  async function runSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const q = query.trim();
    if (!q) return;
    setSearching(true);
    setSearchError("");
    try {
      const res = await searchKnowledge(q, kbId || undefined);
      setHits({ query: res.query, items: res.hits });
    } catch (err) {
      setSearchError(messageOf(err, "Search couldn't be completed."));
      setHits(null);
    } finally {
      setSearching(false);
    }
  }

  const selected = bases?.find((b) => b.id === kbId) ?? null;
  const processed = docs?.filter((d) => d.status === "processed").length ?? 0;

  return (
    <StudioFrame>
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">Knowledge</h1>
      <p className="mt-2 text-muted-foreground">
        Documents your assistants answer from. Uploaded files are processed before they can be
        searched.
      </p>

      {workspace.error && (
        <div className="mt-4">
          <Notice kind="error">{workspace.error}</Notice>
        </div>
      )}
      {workspace.loaded && !workspace.id && !workspace.error && (
        <p className="mt-6 text-muted-foreground">Create a workspace to add knowledge.</p>
      )}
      {!workspace.loaded && !workspace.error && (
        <div className="mt-6">
          <Loading label="Loading your workspace…" />
        </div>
      )}
      {basesError && (
        <div className="mt-4">
          <Notice kind="error">{basesError}</Notice>
        </div>
      )}

      {workspace.id && bases && (
        <>
          <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3" aria-label="Knowledge totals">
            {(
              [
                ["Knowledge bases", bases.length],
                ["Documents", selected ? docsTotal : 0],
                ["Ready in this base", processed],
              ] as const
            ).map(([label, value]) => (
              <div key={label} className="rounded-lg border border-border bg-card p-4">
                <dt className="text-sm text-muted-foreground">{label}</dt>
                <dd className="mt-1 text-2xl font-semibold">{value}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            {bases.length > 0 && (
              <>
                <label htmlFor="kb-select" className="text-sm">
                  Knowledge base
                </label>
                <select
                  id="kb-select"
                  className="rounded-md border border-input bg-background px-3 py-2"
                  value={kbId}
                  onChange={(e) => selectBase(e.target.value)}
                >
                  {bases.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
                {selected && (
                  <>
                    <label htmlFor="kb-status" className="text-sm">
                      Status
                    </label>
                    <select
                      id="kb-status"
                      className="rounded-md border border-input bg-background px-3 py-2"
                      value={selected.status}
                      disabled={statusSaving}
                      onChange={(e) => changeStatus(e.target.value as KnowledgeBaseStatusValue)}
                    >
                      {KNOWLEDGE_BASE_STATUSES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </>
                )}
              </>
            )}
            <Button variant="outline" size="sm" onClick={() => setShowCreate((v) => !v)}>
              <Plus />
              New knowledge base
            </Button>
          </div>
          {selected && (
            <p className="mt-2 text-sm text-muted-foreground">
              Only active knowledge bases are used by assistants and search.
            </p>
          )}
          {statusError && (
            <div className="mt-3">
              <Notice kind="error">{statusError}</Notice>
            </div>
          )}

          {(showCreate || bases.length === 0) && (
            <form onSubmit={createBase} className="mt-4 flex flex-wrap items-end gap-3">
              <label className="grid gap-1 text-sm">
                Name
                <input
                  className="rounded-md border border-input bg-background px-3 py-2"
                  value={newName}
                  maxLength={160}
                  placeholder="Help center"
                  onChange={(e) => setNewName(e.target.value)}
                  required
                />
              </label>
              <Button type="submit" disabled={creating || !newName.trim()}>
                {creating ? "Creating…" : "Create knowledge base"}
              </Button>
              {createError && (
                <div className="w-full">
                  <Notice kind="error">{createError}</Notice>
                </div>
              )}
            </form>
          )}

          {selected && (
            <section className="mt-8" aria-labelledby="kb-documents-heading">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 id="kb-documents-heading" className="text-xl font-semibold">
                  Documents in {selected.name}
                </h2>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setDocsKey((k) => k + 1)}
                    disabled={docs === null && !docsError}
                  >
                    <RefreshCw />
                    Refresh
                  </Button>
                  <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-input px-3 py-2 text-sm hover:bg-accent">
                    <Upload className="size-4" />
                    {uploading ? "Uploading…" : "Upload document"}
                    <input
                      type="file"
                      accept=".pdf,.docx,.txt,.md,text/plain,text/markdown,application/pdf"
                      className="sr-only"
                      disabled={uploading}
                      onChange={uploadFile}
                      aria-label="Upload a document"
                    />
                  </label>
                </div>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                PDF, DOCX, TXT or Markdown, up to {MAX_UPLOAD_MB} MB.
              </p>

              {uploadError && (
                <div className="mt-3">
                  <Notice kind="error">{uploadError}</Notice>
                </div>
              )}
              {deleteError && (
                <div className="mt-3">
                  <Notice kind="error">{deleteError}</Notice>
                </div>
              )}
              {docsError && (
                <div className="mt-3">
                  <Notice kind="error">{docsError}</Notice>
                </div>
              )}

              <div className="mt-4">
                {docs === null && !docsError ? (
                  <Loading label="Loading documents…" />
                ) : docs && docs.length === 0 ? (
                  <p className="text-muted-foreground">
                    No documents yet. Upload a file to add it to this knowledge base.
                  </p>
                ) : docs ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-border text-muted-foreground">
                          <th className="py-2 pr-4 font-medium">Document</th>
                          <th className="py-2 pr-4 font-medium">Status</th>
                          <th className="py-2 pr-4 font-medium">Chunks</th>
                          <th className="py-2 pr-4 font-medium">Uploaded</th>
                          <th className="py-2 font-medium">
                            <span className="sr-only">Actions</span>
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {docs.map((doc) => (
                          <tr key={doc.id} className="border-b border-border align-top">
                            <td className="py-2 pr-4">
                              <span className="font-medium">{doc.filename}</span>
                              {doc.processing_error && (
                                <span className="block text-sm text-destructive">
                                  {doc.processing_error}
                                </span>
                              )}
                            </td>
                            <td className="py-2 pr-4">{STATUS_LABELS[doc.status] ?? doc.status}</td>
                            <td className="py-2 pr-4">{doc.chunk_count}</td>
                            <td className="py-2 pr-4">{when(doc.created_at)}</td>
                            <td className="py-2 text-right">
                              {confirmId === doc.id ? (
                                <span className="inline-flex gap-2">
                                  <Button
                                    variant="destructive"
                                    size="sm"
                                    disabled={deletingId === doc.id}
                                    onClick={() => removeDocument(doc)}
                                  >
                                    {deletingId === doc.id ? "Deleting…" : "Confirm delete"}
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={deletingId === doc.id}
                                    onClick={() => setConfirmId(null)}
                                  >
                                    Cancel
                                  </Button>
                                </span>
                              ) : (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  aria-label={`Delete ${doc.filename}`}
                                  onClick={() => setConfirmId(doc.id)}
                                >
                                  <Trash2 />
                                  Delete
                                </Button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </div>

              <section className="mt-10" aria-labelledby="kb-search-heading">
                <h2 id="kb-search-heading" className="text-xl font-semibold">
                  Search knowledge
                </h2>
                <form onSubmit={runSearch} className="mt-3 flex flex-wrap gap-2">
                  <label className="sr-only" htmlFor="kb-query">
                    Search query
                  </label>
                  <input
                    id="kb-query"
                    className="min-w-0 flex-1 rounded-md border border-input bg-background px-3 py-2"
                    placeholder="Ask a question your documents should answer"
                    value={query}
                    maxLength={500}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  <Button type="submit" variant="outline" disabled={searching || !query.trim()}>
                    {searching ? <Loader2 className="animate-spin" /> : <Search />}
                    Search
                  </Button>
                </form>
                {searchError && (
                  <div className="mt-3">
                    <Notice kind="error">{searchError}</Notice>
                  </div>
                )}
                {hits && (
                  <div className="mt-4">
                    {hits.items.length === 0 ? (
                      <p className="text-muted-foreground">
                        No passages matched “{hits.query}”. Only ready documents in active knowledge
                        bases are searched.
                      </p>
                    ) : (
                      <ul className="grid gap-3" aria-label="Search results">
                        {hits.items.map((hit, i) => (
                          <li
                            key={`${hit.document_id ?? hit.website_page_id ?? "hit"}-${i}`}
                            className="rounded-lg border border-border bg-card p-4"
                          >
                            <span className="block text-sm font-medium">{hit.document}</span>
                            <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">
                              {hit.content}
                            </p>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </section>
            </section>
          )}
        </>
      )}
    </StudioFrame>
  );
}
