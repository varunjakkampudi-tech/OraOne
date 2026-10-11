import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search, Building2, LayoutGrid, Bot, UserPlus, User, BookOpen, Workflow,
  Plug, MessagesSquare, CornerDownLeft,
} from "lucide-react";
import {
  PageHeader, Glass, Badge, SearchInput, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { superAdminApi } from "@/lib/superAdmin";

const ICONS = {
  Building2, LayoutGrid, Bot, UserPlus, User, BookOpen, Workflow, Plug, MessagesSquare,
};

export default function AdminUniversalSearch() {
  const { t } = useAdminTheme();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const timer = useRef(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    const term = q.trim();
    if (term.length < 2) { setData(null); setError(null); setLoading(false); return; }
    setLoading(true);
    timer.current = setTimeout(async () => {
      try {
        const res = await superAdminApi.search(term, 8);
        setData(res); setError(null);
      } catch (e) {
        setError(e?.response?.data?.detail || e.message || "Search failed");
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => timer.current && clearTimeout(timer.current);
  }, [q]);

  const flat = useMemo(
    () => (data?.groups || []).flatMap((g) => g.items.map((it) => ({ ...it, _group: g.label }))),
    [data]
  );

  return (
    <div>
      <PageHeader icon={Search} title="Universal Search"
        subtitle="One box across customers, workspaces, agents, leads, users, knowledge, workflows, integrations & conversations" />

      <Glass className="mb-5 p-3">
        <SearchInput value={q} onChange={setQ} placeholder="Search everything… (try a name, email, or conversation ID)" />
        {data ? (
          <div className="mt-2 px-1 text-xs" style={{ color: t.muted }}>
            {data.total} result{data.total === 1 ? "" : "s"} for “{data.query}”
          </div>
        ) : null}
      </Glass>

      {loading && <LoadingState label="Searching…" />}
      {error && <ErrorState message={error} onRetry={() => setQ((v) => v + " ")} />}

      {!loading && !error && q.trim().length < 2 && (
        <EmptyState icon={Search} title="Start typing to search" hint="Search spans every tenant. Minimum 2 characters." />
      )}

      {!loading && !error && data && flat.length === 0 && q.trim().length >= 2 && (
        <EmptyState icon={Search} title="No matches" hint={`Nothing found for “${data.query}”.`} />
      )}

      {!loading && !error && data && (data.groups || []).map((g) => {
        const Icon = ICONS[g.icon] || Search;
        return (
          <div key={g.type} className="mb-5">
            <div className="mb-2 flex items-center gap-2 px-1">
              <Icon className="h-4 w-4" style={{ color: t.muted }} />
              <span className="text-sm font-semibold" style={{ color: t.ink }}>{g.label}</span>
              <Badge tone="slate">{g.items.length}</Badge>
            </div>
            <div className="space-y-1.5">
              {g.items.map((it) => (
                <Glass key={it.id} hover onClick={() => navigate(it.href)}
                  className="group flex cursor-pointer items-center justify-between p-3">
                  <div className="min-w-0">
                    <div className="truncate font-medium" style={{ color: t.ink }}>{it.title}</div>
                    <div className="truncate text-xs" style={{ color: t.sub }}>{it.subtitle}</div>
                  </div>
                  <CornerDownLeft className="h-4 w-4 shrink-0 opacity-0 transition group-hover:opacity-100" style={{ color: t.muted }} />
                </Glass>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
