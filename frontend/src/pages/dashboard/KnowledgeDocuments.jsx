import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  FileText,
  Search,
  X,
} from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import {
  Badge,
  Card,
  GhostButton,
  PageHeader,
  PrimaryButton,
} from "@/components/dashboard/kit";
import {
  EmptyState,
  ErrorState,
  TableSkeleton,
} from "@/components/dashboard/states";

const PAGE_SIZE = 20;
const STATUS_TONE = {
  processed: "green",
  processing: "blue",
  pending: "blue",
  failed: "red",
};

const formatSize = (bytes) => {
  if (!Number.isFinite(bytes) || bytes <= 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDate = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleDateString();
};

const labelize = (value) =>
  String(value || "unknown")
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function KnowledgeDocuments() {
  const [documents, setDocuments] = useState([]);
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [total, setTotal] = useState(0);
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [knowledgeBaseId, setKnowledgeBaseId] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filterLoading, setFilterLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterError, setFilterError] = useState(null);

  const loadKnowledgeBases = useCallback(async () => {
    setFilterLoading(true);
    setFilterError(null);
    try {
      const response = await api.get("/knowledge-bases", {
        params: { limit: 100, sort: "name" },
      });
      setKnowledgeBases(response.data?.items || []);
    } catch (err) {
      setFilterError(formatApiError(err.response?.data?.detail || err.message));
    } finally {
      setFilterLoading(false);
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = { limit: PAGE_SIZE, offset: page * PAGE_SIZE };
    if (query) params.q = query;
    if (knowledgeBaseId) params.knowledge_base_id = knowledgeBaseId;
    try {
      const response = await api.get("/documents", { params });
      setDocuments(response.data?.items || []);
      setTotal(response.data?.total || 0);
    } catch (err) {
      setDocuments([]);
      setTotal(0);
      setError(formatApiError(err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }, [knowledgeBaseId, page, query]);

  useEffect(() => {
    loadKnowledgeBases();
  }, [loadKnowledgeBases]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const knowledgeBaseNames = useMemo(
    () =>
      new Map(
        knowledgeBases.map((knowledgeBase) => [
          String(knowledgeBase.id),
          knowledgeBase.name,
        ]),
      ),
    [knowledgeBases],
  );
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasFilters = Boolean(query || knowledgeBaseId);

  const submitSearch = (event) => {
    event.preventDefault();
    setPage(0);
    setQuery(input.trim());
  };

  const clearFilters = () => {
    setInput("");
    setQuery("");
    setKnowledgeBaseId("");
    setPage(0);
  };

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Product 1 · Knowledge"
        title="Documents"
        subtitle="Search and browse the documents available to your knowledge bases."
        icon={FileText}
        actions={
          <PrimaryButton as={Link} to="/app/knowledge-base">
            <BookOpen size={16} /> Manage knowledge bases
          </PrimaryButton>
        }
      />

      <Card className="p-4">
        <form
          className="flex flex-col gap-3 lg:flex-row lg:items-end"
          onSubmit={submitSearch}
          role="search"
        >
          <label className="min-w-0 flex-1">
            <span className="mb-1.5 block text-xs font-semibold text-body">
              Search documents
            </span>
            <span className="relative block">
              <Search
                size={16}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
                aria-hidden="true"
              />
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Search by filename"
                className="h-10 w-full rounded-xl border border-stroke bg-white pl-9 pr-3 text-sm text-ink outline-none transition placeholder:text-faint focus:border-brand focus:ring-2 focus:ring-brand/20"
              />
            </span>
          </label>
          <label className="w-full lg:w-72">
            <span className="mb-1.5 block text-xs font-semibold text-body">
              Knowledge base
            </span>
            <select
              value={knowledgeBaseId}
              onChange={(event) => {
                setKnowledgeBaseId(event.target.value);
                setPage(0);
              }}
              disabled={filterLoading || Boolean(filterError)}
              className="h-10 w-full rounded-xl border border-stroke bg-white px-3 text-sm text-ink outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 disabled:cursor-not-allowed disabled:bg-subtle"
            >
              <option value="">All knowledge bases</option>
              {knowledgeBases.map((knowledgeBase) => (
                <option key={knowledgeBase.id} value={knowledgeBase.id}>
                  {knowledgeBase.name}
                </option>
              ))}
            </select>
          </label>
          <div className="flex gap-2">
            <PrimaryButton type="submit">
              <Search size={15} /> Search
            </PrimaryButton>
            {hasFilters && (
              <GhostButton type="button" onClick={clearFilters}>
                <X size={15} /> Clear
              </GhostButton>
            )}
          </div>
        </form>
        {filterError && (
          <p className="mt-3 text-xs text-danger" role="alert">
            Knowledge-base filter unavailable: {filterError}
          </p>
        )}
      </Card>

      {loading ? (
        <TableSkeleton rows={6} cols={4} />
      ) : error ? (
        <ErrorState
          title="Documents unavailable"
          message={error}
          onRetry={loadDocuments}
        />
      ) : documents.length === 0 ? (
        <EmptyState
          icon={FileText}
          title={
            hasFilters ? "No documents match these filters" : "No documents yet"
          }
          hint={
            hasFilters
              ? "Try a different filename or knowledge base."
              : "Add documents from a knowledge base to make them available to your agents."
          }
          action={
            hasFilters ? (
              <GhostButton onClick={clearFilters}>
                <X size={15} /> Clear filters
              </GhostButton>
            ) : (
              <PrimaryButton as={Link} to="/app/knowledge-base">
                <BookOpen size={15} /> Open knowledge bases
              </PrimaryButton>
            )
          }
        />
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left">
              <caption className="sr-only">Knowledge documents</caption>
              <thead className="border-b border-hairline bg-subtle text-xs font-semibold uppercase tracking-wide text-faint">
                <tr>
                  <th scope="col" className="px-5 py-3">
                    Document
                  </th>
                  <th scope="col" className="px-5 py-3">
                    Knowledge base
                  </th>
                  <th scope="col" className="px-5 py-3">
                    Status
                  </th>
                  <th scope="col" className="px-5 py-3">
                    Size
                  </th>
                  <th scope="col" className="px-5 py-3">
                    Added
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline">
                {documents.map((document) => {
                  const kbId = String(document.knowledge_base_id);
                  const kbName =
                    knowledgeBaseNames.get(kbId) ||
                    `Knowledge base ${kbId.slice(0, 8)}`;
                  return (
                    <tr key={document.id} className="transition hover:bg-wash">
                      <td className="px-5 py-4">
                        <p
                          className="max-w-[260px] truncate text-sm font-semibold text-ink"
                          title={document.filename}
                        >
                          {document.filename}
                        </p>
                        <p className="mt-0.5 text-xs text-sub">
                          {document.file_type || "Document"}
                        </p>
                      </td>
                      <td className="px-5 py-4 text-sm">
                        <Link
                          className="font-semibold text-brand hover:underline"
                          to={`/app/knowledge-base/${document.knowledge_base_id}`}
                        >
                          {kbName}
                        </Link>
                      </td>
                      <td className="px-5 py-4">
                        <Badge tone={STATUS_TONE[document.status] || "slate"}>
                          {labelize(document.status)}
                        </Badge>
                      </td>
                      <td className="px-5 py-4 text-sm text-sub">
                        {formatSize(document.file_size)}
                      </td>
                      <td className="px-5 py-4 text-sm text-sub">
                        {formatDate(document.created_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="flex flex-col gap-3 border-t border-hairline px-5 py-3 text-sm text-sub sm:flex-row sm:items-center sm:justify-between">
            <span>
              Showing {page * PAGE_SIZE + 1}–
              {Math.min((page + 1) * PAGE_SIZE, total)} of {total}
            </span>
            <div className="flex items-center gap-2">
              <GhostButton
                type="button"
                disabled={page === 0}
                onClick={() => setPage((current) => Math.max(0, current - 1))}
              >
                <ChevronLeft size={15} /> Previous
              </GhostButton>
              <span className="px-1 text-xs font-semibold text-body">
                Page {page + 1} of {pageCount}
              </span>
              <GhostButton
                type="button"
                disabled={page + 1 >= pageCount}
                onClick={() =>
                  setPage((current) => Math.min(pageCount - 1, current + 1))
                }
              >
                Next <ChevronRight size={15} />
              </GhostButton>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
