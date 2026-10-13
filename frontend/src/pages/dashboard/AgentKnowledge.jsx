import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { BookOpen, Bot, Check, RefreshCw, Save } from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import {
  Card,
  EmptyState,
  GhostButton,
  PageHeader,
  PrimaryButton,
} from "@/components/dashboard/kit";
import { ErrorState, Skeleton } from "@/components/dashboard/states";

function listItems(data) {
  return Array.isArray(data) ? data : data?.items || [];
}

export default function AgentKnowledge() {
  const { id: agentId } = useParams();
  const [agent, setAgent] = useState(null);
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [hasExplicitSelection, setHasExplicitSelection] = useState(false);
  const [savedIds, setSavedIds] = useState([]);
  const [savedExplicitly, setSavedExplicitly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!agentId) {
      setError("No assistant was specified.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");
    try {
      const [{ data: agentData }, { data: basesData }] = await Promise.all([
        api.get(`/agents/${agentId}`),
        api.get("/knowledge-bases", { params: { limit: 100 } }),
      ]);
      const explicitIds = Array.isArray(agentData.knowledge_base_ids);
      const ids = explicitIds ? agentData.knowledge_base_ids : [];
      setAgent(agentData);
      setKnowledgeBases(listItems(basesData));
      setSelectedIds(ids);
      setSavedIds(ids);
      setHasExplicitSelection(explicitIds);
      setSavedExplicitly(explicitIds);
    } catch (err) {
      setError(
        formatApiError(err?.response?.data?.detail) ||
          "The assistant knowledge settings could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    load();
  }, [load]);

  const dirty = useMemo(
    () =>
      hasExplicitSelection !== savedExplicitly ||
      selectedIds.length !== savedIds.length ||
      selectedIds.some((id) => !savedIds.includes(id)),
    [hasExplicitSelection, savedExplicitly, savedIds, selectedIds],
  );

  const toggle = (id) => {
    setHasExplicitSelection(true);
    setSelectedIds((current) =>
      current.includes(id)
        ? current.filter((selectedId) => selectedId !== id)
        : [...current, id],
    );
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put(`/agents/${agentId}`, {
        knowledge_base_ids: selectedIds,
      });
      const ids = Array.isArray(data.knowledge_base_ids)
        ? data.knowledge_base_ids
        : [];
      const explicit = Array.isArray(data.knowledge_base_ids);
      setAgent(data);
      setSelectedIds(ids);
      setSavedIds(ids);
      setHasExplicitSelection(explicit);
      setSavedExplicitly(explicit);
      toast.success("Knowledge binding saved");
    } catch (err) {
      toast.error(
        formatApiError(err?.response?.data?.detail) ||
          "The knowledge binding could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="agent-knowledge-loading">
        <Skeleton className="h-10 w-80" />
        <Skeleton className="h-28 w-full rounded-2xl" />
        <Skeleton className="h-56 w-full rounded-2xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6" data-testid="agent-knowledge-error">
        <PageHeader
          eyebrow="Assistant"
          title="Knowledge binding"
          icon={BookOpen}
        />
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="agent-knowledge-page">
      <PageHeader
        eyebrow="Assistant knowledge"
        title={agent?.name || "Knowledge binding"}
        subtitle="Choose which knowledge bases this assistant can use at runtime."
        icon={Bot}
        actions={
          <PrimaryButton onClick={save} disabled={saving || !dirty}>
            <Save size={15} /> {saving ? "Saving…" : "Save binding"}
          </PrimaryButton>
        }
      />

      <Card className="p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-ink">Knowledge bases</h2>
            <p className="mt-1 text-sm text-sub">
              {hasExplicitSelection
                ? `${selectedIds.length} explicitly selected`
                : "No explicit selection; the assistant keeps its default knowledge behavior."}
            </p>
          </div>
          {dirty && (
            <GhostButton onClick={load} disabled={saving}>
              <RefreshCw size={15} /> Discard changes
            </GhostButton>
          )}
        </div>

        {knowledgeBases.length === 0 ? (
          <div className="mt-5" data-testid="agent-knowledge-empty">
            <EmptyState
              icon={BookOpen}
              title="No knowledge bases available"
              hint="Create a knowledge base in this project before binding it to the assistant."
              action={
                <GhostButton as={Link} to="/app/knowledge-base">
                  Open knowledge bases
                </GhostButton>
              }
            />
          </div>
        ) : (
          <div
            className="mt-5 grid gap-3 sm:grid-cols-2"
            data-testid="agent-knowledge-list"
          >
            {knowledgeBases.map((knowledgeBase) => {
              const selected = selectedIds.includes(knowledgeBase.id);
              return (
                <label
                  key={knowledgeBase.id}
                  className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition-colors ${
                    selected
                      ? "border-brand bg-brand-soft"
                      : "border-line bg-white hover:bg-wash"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => toggle(knowledgeBase.id)}
                    className="mt-1 size-4 accent-brand"
                    data-testid={`agent-knowledge-checkbox-${knowledgeBase.id}`}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2 text-sm font-semibold text-ink">
                      <BookOpen size={15} className="shrink-0 text-brand" />
                      <span className="truncate">{knowledgeBase.name}</span>
                      {selected && (
                        <Check
                          size={15}
                          className="ml-auto shrink-0 text-brand"
                        />
                      )}
                    </span>
                    <span className="mt-1 block text-xs text-sub">
                      {knowledgeBase.description || "No description"}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
