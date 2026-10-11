import React, { useEffect, useState } from "react";
import {
  History, Loader2, GitBranch, RotateCcw, Plus, AlertTriangle,
  Check, ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import {
  PageHeader, Card, Badge, SectionTitle, PrimaryButton, GhostButton,
  EmptyState, INK, SUB, LINE, BRAND,
} from "@/components/dashboard/kit";
import { api, formatApiError } from "@/lib/api";
import { agentVersionsApi } from "@/lib/agentVersions";

function timeAgo(iso) {
  if (!iso) return "";
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

function DiffViewer({ diff }) {
  if (!diff) return null;
  const p = diff.prompt_diff || {};
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <SectionTitle icon={GitBranch} title="Prompt diff"
          subtitle={`${diff.from?.label || "—"} → ${diff.to?.label || "—"}`} />
        <div className="flex items-center gap-2 text-xs">
          <Badge tone="green">+{p.added || 0}</Badge>
          <Badge tone="red">-{p.removed || 0}</Badge>
          <Badge tone="slate">{p.similarity ?? 0}% similar</Badge>
        </div>
      </div>

      {diff.field_changes?.length > 0 && (
        <div className="mt-4 space-y-2">
          {diff.field_changes.map((c, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span className="font-medium" style={{ color: INK }}>{c.field}</span>
              <span className="rounded bg-[#FEE2E2] px-1.5 py-0.5 text-[#B91C1C]">{String(c.from ?? "—")}</span>
              <ArrowRight className="h-3.5 w-3.5" style={{ color: SUB }} />
              <span className="rounded bg-[#DCFCE7] px-1.5 py-0.5 text-[#15803D]">{String(c.to ?? "—")}</span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 overflow-x-auto rounded-xl border font-mono text-[12px] leading-relaxed"
        style={{ borderColor: LINE }}>
        {!p.changed ? (
          <div className="p-4 text-center" style={{ color: SUB }}>No prompt changes between these versions.</div>
        ) : (
          (p.lines || []).map((ln, i) => {
            const bg = ln.type === "add" ? "#F0FDF4" : ln.type === "remove" ? "#FEF2F2"
              : ln.type === "hunk" ? "#F1F5F9" : "transparent";
            const color = ln.type === "add" ? "#15803D" : ln.type === "remove" ? "#B91C1C"
              : ln.type === "hunk" ? "#64748B" : INK;
            const prefix = ln.type === "add" ? "+" : ln.type === "remove" ? "-" : ln.type === "hunk" ? "" : " ";
            return (
              <div key={i} className="whitespace-pre-wrap px-3 py-0.5" style={{ background: bg, color }}>
                {prefix}{ln.text}
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}

export default function AgentVersions() {
  const [agents, setAgents] = useState([]);
  const [agentId, setAgentId] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [label, setLabel] = useState("");
  const [compare, setCompare] = useState({ from: null, to: 0 });
  const [diff, setDiff] = useState(null);

  useEffect(() => {
    api.get("/agents").then(({ data }) => {
      const list = Array.isArray(data) ? data : data?.items || [];
      setAgents(list);
      if (list[0]) setAgentId(list[0].id);
    }).catch(() => setAgents([]));
  }, []);

  const load = (id) => {
    if (!id) return;
    setLoading(true);
    setError("");
    setDiff(null);
    agentVersionsApi
      .list(id)
      .then((d) => {
        setData(d);
        const vs = d.versions || [];
        setCompare({ from: vs[1]?.version ?? vs[0]?.version ?? null, to: 0 });
      })
      .catch((e) => setError(formatApiError(e?.response?.data?.detail) || "Failed to load versions"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { if (agentId) load(agentId); /* eslint-disable-next-line */ }, [agentId]);

  const publish = () => {
    setPublishing(true);
    agentVersionsApi
      .publish(agentId, { label: label.trim() || undefined })
      .then(() => { toast.success("Version published"); setLabel(""); load(agentId); })
      .catch((e) => toast.error(formatApiError(e?.response?.data?.detail) || "Publish failed"))
      .finally(() => setPublishing(false));
  };

  const restore = (version) => {
    agentVersionsApi
      .restore(agentId, version)
      .then(() => { toast.success(`Rolled back to v${version}`); load(agentId); })
      .catch((e) => toast.error(formatApiError(e?.response?.data?.detail) || "Restore failed"));
  };

  const runDiff = () => {
    agentVersionsApi
      .diff(agentId, compare.from ?? 0, compare.to ?? 0)
      .then(setDiff)
      .catch((e) => toast.error(formatApiError(e?.response?.data?.detail) || "Diff failed"));
  };

  const versions = data?.versions || [];

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        icon={History}
        eyebrow="Workspace Intelligence"
        title="Agent Versions"
        subtitle="Publish snapshots of your agent's brain, compare changes, and roll back safely."
      />

      <Card className="p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[220px]">
            <label className="text-xs font-semibold uppercase tracking-wide" style={{ color: SUB }}>Agent</label>
            <select value={agentId} onChange={(e) => setAgentId(e.target.value)}
              className="mt-1.5 w-full rounded-xl border py-2.5 px-3 text-sm outline-none" style={{ borderColor: LINE, color: INK }}>
              {agents.length === 0 && <option value="">No agents yet</option>}
              {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="text-xs font-semibold uppercase tracking-wide" style={{ color: SUB }}>Version label (optional)</label>
            <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Tighter pricing answers"
              className="mt-1.5 w-full rounded-xl border py-2.5 px-3 text-sm outline-none" style={{ borderColor: LINE, color: INK }} />
          </div>
          <PrimaryButton onClick={publish} disabled={publishing || !agentId}>
            {publishing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Publish version
          </PrimaryButton>
        </div>
      </Card>

      {loading ? (
        <div className="grid place-items-center py-16" style={{ color: SUB }}><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : error ? (
        <Card className="mt-6 p-8"><EmptyState icon={AlertTriangle} title="Couldn't load versions" hint={error} /></Card>
      ) : (
        <div className="mt-6 space-y-6">
          {versions.length >= 1 && (
            <Card className="p-5">
              <SectionTitle icon={GitBranch} title="Compare versions" />
              <div className="mt-3 flex flex-wrap items-end gap-3">
                <div>
                  <label className="text-xs" style={{ color: SUB }}>From</label>
                  <select value={compare.from ?? 0} onChange={(e) => setCompare((c) => ({ ...c, from: Number(e.target.value) }))}
                    className="mt-1 block rounded-lg border py-2 px-3 text-sm outline-none" style={{ borderColor: LINE, color: INK }}>
                    {versions.map((v) => <option key={v.version} value={v.version}>v{v.version} — {v.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs" style={{ color: SUB }}>To</label>
                  <select value={compare.to ?? 0} onChange={(e) => setCompare((c) => ({ ...c, to: Number(e.target.value) }))}
                    className="mt-1 block rounded-lg border py-2 px-3 text-sm outline-none" style={{ borderColor: LINE, color: INK }}>
                    <option value={0}>Current (unpublished)</option>
                    {versions.map((v) => <option key={v.version} value={v.version}>v{v.version} — {v.label}</option>)}
                  </select>
                </div>
                <GhostButton onClick={runDiff}><GitBranch className="h-4 w-4" />Compare</GhostButton>
              </div>
            </Card>
          )}

          {diff && <DiffViewer diff={diff} />}

          <Card className="p-6">
            <SectionTitle icon={History} title="Version history" subtitle={`${versions.length} published`} />
            {versions.length === 0 ? (
              <div className="mt-4"><EmptyState icon={History} title="No versions yet"
                hint="Publish your first version to start tracking changes." /></div>
            ) : (
              <div className="mt-4 space-y-3">
                {versions.map((v) => (
                  <div key={v.version} className="flex items-start justify-between gap-3 rounded-xl border p-4" style={{ borderColor: LINE }}>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold" style={{ color: INK }}>v{v.version}</span>
                        <span className="text-sm" style={{ color: INK }}>{v.label}</span>
                        {v.is_current && <Badge tone="green"><Check className="mr-0.5 inline h-3 w-3" />current</Badge>}
                      </div>
                      {v.note && <p className="mt-1 text-sm" style={{ color: SUB }}>{v.note}</p>}
                      <p className="mt-1 truncate text-xs" style={{ color: SUB }}>
                        {(v.system_prompt || "No prompt").slice(0, 120)}
                      </p>
                      <p className="mt-1 text-xs" style={{ color: SUB }}>{timeAgo(v.created_at)}</p>
                    </div>
                    {!v.is_current && (
                      <GhostButton onClick={() => restore(v.version)} className="shrink-0">
                        <RotateCcw className="h-4 w-4" />Restore
                      </GhostButton>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
