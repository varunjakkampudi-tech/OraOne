import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CloudUpload,
  FileText,
  Layers,
  Trash2,
  Folder,
  FolderPlus,
  FolderInput,
  Search,
  Tag,
  RefreshCw,
  X,
  Sparkles,
  History,
  CheckSquare,
  Square,
  Plus,
  Pencil,
  ChevronRight,
  Globe,
  Type,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";

const STATUS_BADGE = {
  pending: "bg-[#FEF3C7] text-[#92400E]",
  processing: "bg-blue-50 text-blue-700",
  processed: "bg-green-50 text-green-700",
  failed: "bg-red-50 text-red-700",
};

const KB_STATUS_BADGE = {
  draft: "bg-[#F1F5F9] text-[#64748B]",
  active: "bg-green-50 text-green-700",
  archived: "bg-amber-50 text-amber-700",
};

const ACCEPT =
  ".pdf,.docx,.txt,.md,.markdown,.csv,.xlsx,.xlsm,.pptx,.json,.html,.htm";

function humanSize(bytes) {
  if (bytes == null) return "—";
  const u = ["B", "KB", "MB", "GB"];
  let i = 0;
  let v = bytes;
  while (v >= 1024 && i < u.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(v < 10 && i > 0 ? 1 : 0)} ${u[i]}`;
}

export default function KnowledgeBaseDetails() {
  const { id } = useParams();
  const nav = useNavigate();
  const fileRef = useRef(null);

  const [kb, setKb] = useState(null);
  const [docs, setDocs] = useState([]);
  const [folders, setFolders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [drag, setDrag] = useState(false);

  // organization state
  const [selectedFolder, setSelectedFolder] = useState(null); // null = all, "unfiled", or folder id
  const [selected, setSelected] = useState(() => new Set()); // bulk-selected doc ids
  const [moveOpen, setMoveOpen] = useState(false);
  const [textOpen, setTextOpen] = useState(false);
  const [textTitle, setTextTitle] = useState("");
  const [textBody, setTextBody] = useState("");

  // search
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState(null);

  // preview drawer
  const [previewDoc, setPreviewDoc] = useState(null);

  const load = useCallback(async () => {
    try {
      const [{ data: kbData }, { data: docList }, { data: folderList }] =
        await Promise.all([
          api.get(`/knowledge-bases/${id}`),
          api.get("/documents", { params: { knowledge_base_id: id } }),
          api.get("/knowledge-folders", { params: { knowledge_base_id: id } }),
        ]);
      setKb(kbData);
      setDocs(docList.items || []);
      setFolders(folderList || []);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
      nav("/app/knowledge-base");
    } finally {
      setLoading(false);
    }
  }, [id, nav]);

  useEffect(() => {
    load();
  }, [load]);

  // Poll while any document is still being processed.
  useEffect(() => {
    const inFlight = docs.some(
      (d) => d.status === "pending" || d.status === "processing"
    );
    if (!inFlight) return undefined;
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [docs, load]);

  const visibleDocs = useMemo(() => {
    if (selectedFolder === null) return docs;
    if (selectedFolder === "unfiled") return docs.filter((d) => !d.folder_id);
    return docs.filter((d) => d.folder_id === selectedFolder);
  }, [docs, selectedFolder]);

  const unfiledCount = useMemo(
    () => docs.filter((d) => !d.folder_id).length,
    [docs]
  );

  /* ----------------------------- uploads ----------------------------- */
  const upload = async (files) => {
    const list = Array.from(files || []);
    if (list.length === 0) return;
    setUploading(true);
    try {
      for (const f of list) {
        const fd = new FormData();
        fd.append("knowledge_base_id", id);
        fd.append("file", f);
        if (selectedFolder && selectedFolder !== "unfiled") {
          fd.append("folder_id", selectedFolder);
        }
        await api.post("/documents/upload", fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
      toast.success(`Uploaded ${list.length} file${list.length > 1 ? "s" : ""}`);
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setUploading(false);
    }
  };

  const remove = async (doc) => {
    if (!window.confirm(`Delete "${doc.filename}"?`)) return;
    try {
      await api.delete(`/documents/${doc.id}`);
      toast.success("Document deleted");
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  /* --------------------- multi-source ingestion (Phase R) --------------------- */
  const addWebsite = async () => {
    const url = window.prompt("Enter a public web page URL to import (https://…)");
    if (!url || !url.trim()) return;
    setUploading(true);
    try {
      await api.post("/knowledge/sources/website", {
        knowledge_base_id: id,
        url: url.trim(),
        folder_id: selectedFolder && selectedFolder !== "unfiled" ? selectedFolder : undefined,
      });
      toast.success("Web page imported — indexing now");
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setUploading(false);
    }
  };

  const addText = async () => {
    if (!textTitle.trim() || !textBody.trim()) {
      toast.error("Add a title and some content first");
      return;
    }
    setUploading(true);
    try {
      await api.post("/knowledge/sources/text", {
        knowledge_base_id: id,
        title: textTitle.trim(),
        content: textBody,
        folder_id: selectedFolder && selectedFolder !== "unfiled" ? selectedFolder : undefined,
      });
      toast.success("Text added — indexing now");
      setTextOpen(false);
      setTextTitle("");
      setTextBody("");
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setUploading(false);
    }
  };

  /* ----------------------------- folders ----------------------------- */
  const createFolder = async () => {
    const name = window.prompt("Folder name");
    if (!name || !name.trim()) return;
    try {
      await api.post("/knowledge-folders", {
        knowledge_base_id: id,
        name: name.trim(),
      });
      toast.success("Folder created");
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const renameFolder = async (folder) => {
    const name = window.prompt("Rename folder", folder.name);
    if (!name || !name.trim() || name.trim() === folder.name) return;
    try {
      await api.put(`/knowledge-folders/${folder.id}`, { name: name.trim() });
      toast.success("Folder renamed");
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const deleteFolder = async (folder) => {
    if (!window.confirm(`Delete folder "${folder.name}"? Documents inside move to Unfiled.`))
      return;
    try {
      await api.delete(`/knowledge-folders/${folder.id}`);
      if (selectedFolder === folder.id) setSelectedFolder(null);
      toast.success("Folder deleted");
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  /* ----------------------------- bulk ----------------------------- */
  const toggleSelect = (docId) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) next.delete(docId);
      else next.add(docId);
      return next;
    });
  };

  const allVisibleSelected =
    visibleDocs.length > 0 && visibleDocs.every((d) => selected.has(d.id));

  const toggleSelectAll = () => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (allVisibleSelected) visibleDocs.forEach((d) => next.delete(d.id));
      else visibleDocs.forEach((d) => next.add(d.id));
      return next;
    });
  };

  const clearSelection = () => setSelected(new Set());

  const bulk = async (payload, successMsg) => {
    try {
      const ids = Array.from(selected);
      const { data } = await api.post("/documents/bulk", {
        document_ids: ids,
        ...payload,
      });
      toast.success(successMsg(data?.affected ?? ids.length));
      clearSelection();
      setMoveOpen(false);
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const bulkDelete = () => {
    if (!window.confirm(`Delete ${selected.size} document(s)?`)) return;
    bulk({ action: "delete" }, (n) => `Deleted ${n} document(s)`);
  };

  const bulkReprocess = () =>
    bulk({ action: "reprocess" }, (n) => `Reprocessing ${n} document(s)`);

  const bulkTag = () => {
    const raw = window.prompt("Add tags (comma-separated)");
    if (!raw || !raw.trim()) return;
    const tags = raw
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    if (tags.length === 0) return;
    bulk({ action: "tag", tags }, (n) => `Tagged ${n} document(s)`);
  };

  const bulkMove = (folderId) => {
    if (folderId === "unfiled") {
      bulk({ action: "move", clear_folder: true }, (n) => `Moved ${n} to Unfiled`);
    } else {
      bulk({ action: "move", folder_id: folderId }, (n) => `Moved ${n} document(s)`);
    }
  };

  /* ----------------------------- search ----------------------------- */
  const runSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    try {
      const { data } = await api.post("/knowledge/search", {
        query: query.trim(),
        knowledge_base_id: id,
        top_k: 8,
      });
      setSearchResults(data);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSearching(false);
    }
  };

  const clearSearch = () => {
    setQuery("");
    setSearchResults(null);
  };

  if (loading || !kb) {
    return <div className="h-48 rounded-2xl skeleton" data-testid="kb-details-loading" />;
  }

  const folderName = (fid) => folders.find((f) => f.id === fid)?.name;

  return (
    <div className="space-y-6" data-testid="kb-details-page">
      <button
        onClick={() => nav("/app/knowledge-base")}
        className="text-sm text-[#64748B] hover:text-[#0F172A] inline-flex items-center gap-1.5"
      >
        <ArrowLeft size={14} /> Back to Knowledge Bases
      </button>

      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2
              className="text-2xl sm:text-3xl font-bold tracking-tight text-[#0F172A]"
              data-testid="kb-details-name"
            >
              {kb.name}
            </h2>
            <span
              className={`text-[10px] px-2 py-0.5 rounded-full font-semibold capitalize ${
                KB_STATUS_BADGE[kb.status] || KB_STATUS_BADGE.draft
              }`}
            >
              {kb.status}
            </span>
          </div>
          {kb.description && (
            <p className="text-sm text-[#64748B] mt-1 max-w-2xl">{kb.description}</p>
          )}
        </div>
        <div className="flex items-center gap-3 text-sm">
          <Stat label="Documents" value={kb.document_count} icon={FileText} />
          <Stat
            label="Chunks"
            value={docs.reduce((s, d) => s + (d.chunk_count || 0), 0)}
            icon={Layers}
          />
          <Stat
            label="Embeddings"
            value={docs.reduce((s, d) => s + (d.embedded_count || 0), 0)}
            icon={Sparkles}
          />
        </div>
      </div>

      {/* Knowledge search */}
      <form onSubmit={runSearch} className="relative" data-testid="kb-search-form">
        <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search across this knowledge base…"
          data-testid="kb-search-input"
          className="w-full pl-10 pr-28 py-3 rounded-2xl border border-[#E2E8F0] bg-white text-sm placeholder-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10"
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {(query || searchResults) && (
            <button
              type="button"
              onClick={clearSearch}
              className="p-1.5 rounded-lg text-[#94A3B8] hover:text-[#0F172A]"
              aria-label="Clear search"
            >
              <X size={15} />
            </button>
          )}
          <button
            type="submit"
            disabled={searching}
            className="px-3.5 py-1.5 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold disabled:opacity-60"
          >
            {searching ? "Searching…" : "Search"}
          </button>
        </div>
      </form>

      {searchResults && (
        <div
          className="rounded-2xl border border-[#E2E8F0] bg-white overflow-hidden"
          data-testid="kb-search-results"
        >
          <div className="px-5 py-3 border-b border-[#E2E8F0] flex items-center justify-between">
            <h3 className="text-sm font-semibold text-[#0F172A]">
              Search results for “{searchResults.query}”
            </h3>
            <span className="text-xs text-[#64748B]">
              {searchResults.hits.length} match
              {searchResults.hits.length === 1 ? "" : "es"}
            </span>
          </div>
          {searchResults.hits.length === 0 ? (
            <div className="p-8 text-center text-sm text-[#64748B]">
              No matching content found.
            </div>
          ) : (
            <ul className="divide-y divide-[#E2E8F0]">
              {searchResults.hits.map((h, i) => (
                <li key={i} className="px-5 py-3" data-testid="kb-search-hit">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText size={13} className="text-[#475569]" />
                    <span className="text-xs font-semibold text-[#0F172A]">
                      {h.document}
                    </span>
                    {h.page != null && (
                      <span className="text-[10px] text-[#94A3B8]">· page {h.page}</span>
                    )}
                    {h.section && (
                      <span className="text-[10px] text-[#94A3B8] truncate">· {h.section}</span>
                    )}
                    {h.score != null && (
                      <span className="ml-auto text-[10px] text-[#94A3B8]">
                        {(h.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-[#334155] line-clamp-3">{h.content}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Uploader */}
      <div
        onDragEnter={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          upload(e.dataTransfer.files);
        }}
        className={`p-8 rounded-3xl border-2 border-dashed text-center transition-colors ${
          drag ? "border-[#2563EB] bg-[#EFF6FF]" : "border-[#CBD5E1] bg-white"
        }`}
        data-testid="kb-details-dropzone"
      >
        <CloudUpload size={34} className="mx-auto text-[#94A3B8]" />
        <p className="mt-3 text-base font-semibold text-[#0F172A]">
          Drag &amp; drop files here
        </p>
        <p className="text-sm text-[#64748B] mt-1">
          PDF, DOCX, TXT, MD, CSV, XLSX, PPTX, JSON, HTML — up to 25 MB each
          {selectedFolder && selectedFolder !== "unfiled" && (
            <> · uploading to <strong>{folderName(selectedFolder)}</strong></>
          )}
        </p>
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          data-testid="kb-details-upload-btn"
          className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold disabled:opacity-60"
        >
          {uploading ? "Uploading…" : "Choose files"}
        </button>
        <div className="mt-4 flex items-center justify-center gap-2">
          <span className="text-xs text-[#94A3B8]">or add from</span>
          <button
            onClick={addWebsite}
            disabled={uploading}
            data-testid="kb-source-website"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E2E8F0] bg-white text-sm font-medium text-[#334155] hover:border-[#2563EB] hover:text-[#2563EB] disabled:opacity-60"
          >
            <Globe size={15} /> Website
          </button>
          <button
            onClick={() => setTextOpen(true)}
            disabled={uploading}
            data-testid="kb-source-text"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#E2E8F0] bg-white text-sm font-medium text-[#334155] hover:border-[#2563EB] hover:text-[#2563EB] disabled:opacity-60"
          >
            <Type size={15} /> Text / FAQ
          </button>
        </div>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => upload(e.target.files)}
          data-testid="kb-details-file-input"
        />
      </div>

      {/* Folders + documents */}
      <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-5">
        {/* Folders sidebar */}
        <aside className="rounded-2xl border border-[#E2E8F0] bg-white p-2 h-max" data-testid="kb-folders">
          <div className="flex items-center justify-between px-2 py-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-[#94A3B8]">
              Folders
            </span>
            <button
              onClick={createFolder}
              className="p-1 rounded-lg text-[#64748B] hover:text-[#2563EB] hover:bg-[#EFF6FF]"
              aria-label="New folder"
              data-testid="kb-folder-add"
              title="New folder"
            >
              <FolderPlus size={15} />
            </button>
          </div>
          <FolderItem
            active={selectedFolder === null}
            icon={Layers}
            label="All documents"
            count={docs.length}
            onClick={() => setSelectedFolder(null)}
          />
          <FolderItem
            active={selectedFolder === "unfiled"}
            icon={Folder}
            label="Unfiled"
            count={unfiledCount}
            onClick={() => setSelectedFolder("unfiled")}
          />
          <div className="my-1 border-t border-[#F1F5F9]" />
          {folders.length === 0 ? (
            <p className="px-2 py-3 text-[11px] text-[#94A3B8]">
              No folders yet. Create one to organize documents.
            </p>
          ) : (
            folders.map((f) => (
              <FolderItem
                key={f.id}
                active={selectedFolder === f.id}
                icon={Folder}
                label={f.name}
                count={f.document_count}
                color={f.color}
                onClick={() => setSelectedFolder(f.id)}
                onRename={() => renameFolder(f)}
                onDelete={() => deleteFolder(f)}
              />
            ))
          )}
        </aside>

        {/* Documents */}
        <div className="rounded-2xl border border-[#E2E8F0] bg-white overflow-hidden">
          <div className="px-5 py-3 border-b border-[#E2E8F0] flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <button
                onClick={toggleSelectAll}
                disabled={visibleDocs.length === 0}
                className="text-[#64748B] hover:text-[#2563EB] disabled:opacity-40"
                aria-label="Select all"
                data-testid="kb-select-all"
              >
                {allVisibleSelected ? <CheckSquare size={16} /> : <Square size={16} />}
              </button>
              <h3 className="text-sm font-semibold text-[#0F172A]">
                {selectedFolder === null
                  ? "All documents"
                  : selectedFolder === "unfiled"
                  ? "Unfiled"
                  : folderName(selectedFolder)}
              </h3>
            </div>
            <span className="text-xs text-[#64748B]">{visibleDocs.length} shown</span>
          </div>

          {/* Bulk action bar */}
          {selected.size > 0 && (
            <div
              className="px-5 py-2.5 bg-[#EFF6FF] border-b border-[#DBEAFE] flex items-center flex-wrap gap-2"
              data-testid="kb-bulk-bar"
            >
              <span className="text-xs font-semibold text-[#1D4ED8]">
                {selected.size} selected
              </span>
              <div className="relative">
                <button
                  onClick={() => setMoveOpen((v) => !v)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-[#BFDBFE] text-xs font-medium text-[#1D4ED8] hover:bg-[#F8FAFC]"
                >
                  <FolderInput size={13} /> Move <ChevronRight size={12} className="rotate-90" />
                </button>
                {moveOpen && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setMoveOpen(false)} />
                    <div className="absolute left-0 top-9 z-20 w-48 rounded-xl bg-white border border-[#E2E8F0] shadow-xl py-1 text-[13px] max-h-64 overflow-y-auto">
                      <button
                        onClick={() => bulkMove("unfiled")}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-left text-[#334155] hover:bg-[#F8FAFC]"
                      >
                        <Folder size={13} /> Unfiled
                      </button>
                      {folders.map((f) => (
                        <button
                          key={f.id}
                          onClick={() => bulkMove(f.id)}
                          className="w-full flex items-center gap-2 px-3 py-1.5 text-left text-[#334155] hover:bg-[#F8FAFC]"
                        >
                          <Folder size={13} /> <span className="truncate">{f.name}</span>
                        </button>
                      ))}
                      {folders.length === 0 && (
                        <p className="px-3 py-2 text-[11px] text-[#94A3B8]">No folders</p>
                      )}
                    </div>
                  </>
                )}
              </div>
              <button
                onClick={bulkTag}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-[#BFDBFE] text-xs font-medium text-[#1D4ED8] hover:bg-[#F8FAFC]"
              >
                <Tag size={13} /> Tag
              </button>
              <button
                onClick={bulkReprocess}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-[#BFDBFE] text-xs font-medium text-[#1D4ED8] hover:bg-[#F8FAFC]"
              >
                <RefreshCw size={13} /> Reprocess
              </button>
              <button
                onClick={bulkDelete}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-red-200 text-xs font-medium text-red-600 hover:bg-red-50"
              >
                <Trash2 size={13} /> Delete
              </button>
              <button
                onClick={clearSelection}
                className="ml-auto text-xs text-[#64748B] hover:text-[#0F172A]"
              >
                Clear
              </button>
            </div>
          )}

          {visibleDocs.length === 0 ? (
            <div className="p-10 text-center text-sm text-[#64748B]">
              No documents {selectedFolder ? "in this folder" : "uploaded yet"}.
            </div>
          ) : (
            <ul className="divide-y divide-[#E2E8F0]">
              {visibleDocs.map((d) => (
                <li
                  key={d.id}
                  className={`px-5 py-3 flex items-center gap-3 transition-colors ${
                    selected.has(d.id) ? "bg-[#F8FAFF]" : ""
                  }`}
                  data-testid={`kb-doc-${d.id}`}
                >
                  <button
                    onClick={() => toggleSelect(d.id)}
                    className="text-[#94A3B8] hover:text-[#2563EB]"
                    aria-label="Select document"
                    data-testid={`kb-doc-select-${d.id}`}
                  >
                    {selected.has(d.id) ? (
                      <CheckSquare size={16} className="text-[#2563EB]" />
                    ) : (
                      <Square size={16} />
                    )}
                  </button>
                  <div className="size-9 rounded-xl bg-[#F1F5F9] grid place-items-center shrink-0">
                    <FileText size={16} className="text-[#475569]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <button
                      onClick={() => setPreviewDoc(d)}
                      className="text-sm font-medium text-[#0F172A] truncate hover:text-[#2563EB] text-left max-w-full"
                      data-testid={`kb-doc-open-${d.id}`}
                    >
                      {d.filename}
                    </button>
                    <p className="text-xs text-[#64748B] mt-0.5 truncate">
                      {d.file_type || "Unknown"} · {humanSize(d.file_size)} ·{" "}
                      {(d.chunk_count || 0).toLocaleString()} chunks
                      {d.chunk_count > 0 && (
                        <>
                          {" · "}
                          <span
                            className={
                              (d.embedded_count || 0) >= (d.chunk_count || 0)
                                ? "text-green-600"
                                : "text-amber-600"
                            }
                            title="Chunks with vector embeddings"
                          >
                            {(d.embedded_count || 0).toLocaleString()} embedded
                          </span>
                        </>
                      )}
                      {d.version > 1 && <> · v{d.version}</>}
                      {d.folder_id && folderName(d.folder_id) && selectedFolder === null && (
                        <> · {folderName(d.folder_id)}</>
                      )}
                      {" · "}
                      {d.processing_completed_at
                        ? `Synced ${new Date(d.processing_completed_at).toLocaleDateString()}`
                        : new Date(d.created_at).toLocaleDateString()}
                    </p>
                    {Array.isArray(d.tags) && d.tags.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {d.tags.map((t) => (
                          <span
                            key={t}
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-[#EFF6FF] text-[10px] text-[#1D4ED8]"
                          >
                            <Tag size={9} /> {t}
                          </span>
                        ))}
                      </div>
                    )}
                    {d.processing_error && (
                      <p
                        className="text-xs text-red-600 mt-1 truncate"
                        title={d.processing_error}
                        data-testid={`kb-doc-error-${d.id}`}
                      >
                        Error: {d.processing_error}
                      </p>
                    )}
                  </div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-semibold capitalize ${
                      STATUS_BADGE[d.status] || STATUS_BADGE.pending
                    }`}
                    data-testid={`kb-doc-status-${d.id}`}
                  >
                    {d.status}
                  </span>
                  {d.status === "failed" && (
                    <button
                      onClick={async () => {
                        try {
                          await api.post(`/documents/${d.id}/process`);
                          toast.success("Reprocessing started");
                          load();
                        } catch (err) {
                          toast.error(formatApiError(err.response?.data?.detail));
                        }
                      }}
                      className="px-3 py-1.5 rounded-xl border border-[#E2E8F0] hover:bg-[#F8FAFC] text-xs font-medium text-[#0F172A]"
                      data-testid={`kb-doc-retry-${d.id}`}
                    >
                      Retry
                    </button>
                  )}
                  <button
                    onClick={() => remove(d)}
                    className="size-9 rounded-xl border border-[#E2E8F0] hover:bg-red-50 hover:border-red-200 grid place-items-center text-red-500"
                    aria-label="Delete"
                    data-testid={`kb-doc-delete-${d.id}`}
                  >
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {previewDoc && (
        <PreviewDrawer
          doc={previewDoc}
          onClose={() => setPreviewDoc(null)}
          onChanged={load}
        />
      )}

      {textOpen && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-[#0F172A] flex items-center gap-2">
                <Type size={18} className="text-[#2563EB]" /> Add text / FAQ
              </h3>
              <button
                onClick={() => setTextOpen(false)}
                className="size-8 grid place-items-center rounded-lg text-[#64748B] hover:bg-[#F1F5F9]"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>
            <p className="mt-1 text-sm text-[#64748B]">
              Paste raw content or Q&amp;A. It will be chunked, embedded and searchable like any document.
            </p>
            <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-[#94A3B8]">
              Title
            </label>
            <input
              value={textTitle}
              onChange={(e) => setTextTitle(e.target.value)}
              placeholder="e.g. Refund policy"
              className="mt-1 w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#2563EB]"
              data-testid="kb-text-title"
            />
            <label className="mt-3 block text-xs font-semibold uppercase tracking-wide text-[#94A3B8]">
              Content
            </label>
            <textarea
              value={textBody}
              onChange={(e) => setTextBody(e.target.value)}
              rows={8}
              placeholder="Paste your text or FAQ here…"
              className="mt-1 w-full resize-y rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#2563EB]"
              data-testid="kb-text-body"
            />
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={() => setTextOpen(false)}
                className="px-4 py-2 rounded-xl border border-[#E2E8F0] text-sm font-medium text-[#334155] hover:bg-[#F8FAFC]"
              >
                Cancel
              </button>
              <button
                onClick={addText}
                disabled={uploading}
                className="px-4 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold disabled:opacity-60"
                data-testid="kb-text-save"
              >
                {uploading ? "Adding…" : "Add to knowledge base"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------ subcomponents ------------------------------ */

function Stat({ label, value, icon: Icon }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white border border-[#E2E8F0]">
      <Icon size={14} className="text-[#475569]" />
      <span className="text-[#64748B]">{label}:</span>
      <span className="font-semibold text-[#0F172A]">
        {(value || 0).toLocaleString()}
      </span>
    </div>
  );
}

function FolderItem({ active, icon: Icon, label, count, color, onClick, onRename, onDelete }) {
  return (
    <div
      className={`group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer transition-colors ${
        active ? "bg-[#EFF6FF]" : "hover:bg-[#F8FAFC]"
      }`}
      onClick={onClick}
      data-testid="kb-folder-item"
    >
      <Icon
        size={15}
        style={color ? { color } : undefined}
        className={active ? "text-[#2563EB]" : "text-[#64748B]"}
      />
      <span
        className={`flex-1 text-sm truncate ${active ? "text-[#2563EB] font-medium" : "text-[#334155]"}`}
      >
        {label}
      </span>
      {(onRename || onDelete) && (
        <span className="hidden group-hover:flex items-center gap-0.5">
          {onRename && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRename();
              }}
              className="p-0.5 rounded text-[#94A3B8] hover:text-[#2563EB]"
              aria-label="Rename folder"
            >
              <Pencil size={12} />
            </button>
          )}
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-0.5 rounded text-[#94A3B8] hover:text-red-500"
              aria-label="Delete folder"
            >
              <Trash2 size={12} />
            </button>
          )}
        </span>
      )}
      <span className="group-hover:hidden text-[11px] text-[#94A3B8] tabular-nums">
        {count ?? 0}
      </span>
    </div>
  );
}

function PreviewDrawer({ doc, onClose, onChanged }) {
  const [data, setData] = useState(null);
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tags, setTags] = useState(doc.tags || []);
  const [tagInput, setTagInput] = useState("");
  const [savingTags, setSavingTags] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [{ data: preview }, { data: vers }] = await Promise.all([
          api.get(`/documents/${doc.id}/preview`),
          api.get(`/documents/${doc.id}/versions`),
        ]);
        if (cancelled) return;
        setData(preview);
        setVersions(vers || []);
        setTags(preview.tags || []);
      } catch (err) {
        if (!cancelled) toast.error(formatApiError(err.response?.data?.detail));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [doc.id]);

  const saveTags = async (next) => {
    setSavingTags(true);
    try {
      await api.patch(`/documents/${doc.id}`, { tags: next });
      setTags(next);
      onChanged?.();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSavingTags(false);
    }
  };

  const addTag = (e) => {
    e.preventDefault();
    const t = tagInput.trim();
    if (!t || tags.includes(t)) {
      setTagInput("");
      return;
    }
    saveTags([...tags, t]);
    setTagInput("");
  };

  const removeTag = (t) => saveTags(tags.filter((x) => x !== t));

  const meta = data?.doc_metadata || {};

  return (
    <div className="fixed inset-0 z-50 flex" data-testid="kb-preview-drawer">
      <div className="flex-1 bg-black/30" onClick={onClose} />
      <div className="w-full max-w-md bg-white h-full overflow-y-auto shadow-2xl flex flex-col">
        <div className="px-5 py-4 border-b border-[#E2E8F0] flex items-start justify-between gap-3 sticky top-0 bg-white">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <FileText size={16} className="text-[#475569] shrink-0" />
              <h3 className="text-sm font-semibold text-[#0F172A] truncate">{doc.filename}</h3>
            </div>
            <p className="text-[11px] text-[#94A3B8] mt-0.5">
              {doc.file_type} · {humanSize(doc.file_size)}
              {doc.version > 1 && <> · v{doc.version}</>}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#94A3B8] hover:text-[#0F172A] hover:bg-[#F1F5F9]"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        {loading ? (
          <div className="p-5 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 rounded-xl skeleton" />
            ))}
          </div>
        ) : (
          <div className="p-5 space-y-6">
            {/* status + embedding stats */}
            <div className="grid grid-cols-2 gap-2">
              <MiniStat
                label="Status"
                value={
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-semibold capitalize ${
                      STATUS_BADGE[doc.status] || STATUS_BADGE.pending
                    }`}
                  >
                    {doc.status || "pending"}
                  </span>
                }
              />
              <MiniStat
                label="Embeddings"
                value={`${(doc.embedded_count || 0).toLocaleString()} / ${(
                  doc.chunk_count || 0
                ).toLocaleString()}`}
              />
              {doc.processing_completed_at && (
                <MiniStat
                  label="Last synced"
                  value={new Date(doc.processing_completed_at).toLocaleString()}
                />
              )}
              {doc.processing_time_ms != null && (
                <MiniStat
                  label="Process time"
                  value={`${(doc.processing_time_ms / 1000).toFixed(1)}s`}
                />
              )}
            </div>
            {/* metadata stats */}
            {Object.keys(meta).length > 0 && (
              <div className="grid grid-cols-2 gap-2">
                {meta.pages != null && <MiniStat label="Pages" value={meta.pages} />}
                {meta.word_count != null && (
                  <MiniStat label="Words" value={meta.word_count.toLocaleString()} />
                )}
                {meta.chunk_count != null && (
                  <MiniStat label="Chunks" value={meta.chunk_count} />
                )}
                {meta.char_count != null && (
                  <MiniStat label="Characters" value={meta.char_count.toLocaleString()} />
                )}
              </div>
            )}

            {/* summary */}
            {data?.summary && (
              <Section icon={Sparkles} title="Summary">
                <p className="text-sm text-[#334155] leading-relaxed">{data.summary}</p>
              </Section>
            )}

            {/* suggested questions */}
            {data?.suggested_questions?.length > 0 && (
              <Section icon={Sparkles} title="Suggested questions">
                <ul className="space-y-1.5">
                  {data.suggested_questions.map((q, i) => (
                    <li
                      key={i}
                      className="text-sm text-[#334155] px-3 py-2 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]"
                    >
                      {q}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {/* tags editor */}
            <Section icon={Tag} title="Tags">
              <div className="flex flex-wrap gap-1.5 mb-2">
                {tags.length === 0 && (
                  <span className="text-xs text-[#94A3B8]">No tags yet.</span>
                )}
                {tags.map((t) => (
                  <span
                    key={t}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#EFF6FF] text-[11px] text-[#1D4ED8]"
                  >
                    {t}
                    <button
                      onClick={() => removeTag(t)}
                      disabled={savingTags}
                      className="hover:text-red-500"
                      aria-label={`Remove ${t}`}
                    >
                      <X size={11} />
                    </button>
                  </span>
                ))}
              </div>
              <form onSubmit={addTag} className="flex items-center gap-2">
                <input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  placeholder="Add a tag…"
                  className="flex-1 px-3 py-1.5 rounded-lg border border-[#E2E8F0] text-sm placeholder-[#94A3B8] focus:border-[#2563EB] focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={savingTags || !tagInput.trim()}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-full bg-[#2563EB] text-white text-xs font-medium disabled:opacity-50"
                >
                  <Plus size={13} /> Add
                </button>
              </form>
            </Section>

            {/* excerpt */}
            {data?.excerpt && (
              <Section icon={FileText} title="Excerpt">
                <p className="text-sm text-[#475569] leading-relaxed whitespace-pre-wrap line-clamp-[12]">
                  {data.excerpt}
                </p>
              </Section>
            )}

            {/* versions */}
            {versions.length > 0 && (
              <Section icon={History} title={`Version history (${versions.length})`}>
                <ul className="space-y-1.5">
                  {versions.map((v) => (
                    <li
                      key={v.id}
                      className="flex items-center justify-between text-xs px-3 py-2 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]"
                    >
                      <span className="font-medium text-[#334155]">v{v.version}</span>
                      <span className="text-[#94A3B8]">{humanSize(v.file_size)}</span>
                      <span className="text-[#94A3B8]">
                        {new Date(v.created_at).toLocaleDateString()}
                      </span>
                    </li>
                  ))}
                </ul>
              </Section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Section({ icon: Icon, title, children }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-2">
        <Icon size={13} className="text-[#2563EB]" />
        <h4 className="text-[11px] font-semibold uppercase tracking-wide text-[#64748B]">
          {title}
        </h4>
      </div>
      {children}
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div className="px-3 py-2 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
      <p className="text-[10px] uppercase tracking-wide text-[#94A3B8]">{label}</p>
      <p className="text-sm font-semibold text-[#0F172A]">{value}</p>
    </div>
  );
}
