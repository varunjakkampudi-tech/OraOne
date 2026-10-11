import React, { useState } from "react";
import { UserSearch, Loader2, Search, AlertTriangle, Mail, Phone, Building2, MessagesSquare, Clock } from "lucide-react";
import {
  PageHeader,
  Card,
  Badge,
  SectionTitle,
  EmptyState,
  INK,
  SUB,
  LINE,
  BRAND,
} from "@/components/dashboard/kit";
import { workspaceIntelApi } from "@/lib/workspaceIntel";
import { formatApiError } from "@/lib/api";

function timeAgo(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

const TEMP = { hot: "red", warm: "amber", cold: "blue" };

export default function Customer360() {
  const [q, setQ] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  const run = (e) => {
    e?.preventDefault?.();
    const query = q.trim();
    if (query.length < 2) return;
    setLoading(true);
    setError("");
    setSearched(true);
    workspaceIntelApi
      .customer360(query)
      .then(setData)
      .catch((e) => setError(formatApiError(e?.response?.data?.detail) || "Search failed"))
      .finally(() => setLoading(false));
  };

  const p = data?.profile || {};
  const stats = data?.stats || {};

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        icon={UserSearch}
        eyebrow="Workspace Intelligence"
        title="Customer 360°"
        subtitle="Search a customer by email, phone or name to see their unified profile and journey."
      />

      <Card className="p-4">
        <form onSubmit={run} className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2" style={{ color: SUB }} />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="e.g. priya@acme.com, +1 555…, or Priya"
              className="w-full rounded-xl border py-2.5 pl-10 pr-3 text-sm outline-none"
              style={{ borderColor: LINE, color: INK }}
            />
          </div>
          <button
            type="submit"
            disabled={loading || q.trim().length < 2}
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            style={{ background: BRAND }}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Search
          </button>
        </form>
      </Card>

      <div className="mt-6">
        {loading ? (
          <div className="grid place-items-center py-20" style={{ color: SUB }}>
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : error ? (
          <Card className="p-8">
            <EmptyState icon={AlertTriangle} title="Search failed" hint={error} />
          </Card>
        ) : !searched ? (
          <Card className="p-8">
            <EmptyState icon={UserSearch} title="Find a customer"
              hint="Search above to assemble a 360° view across conversations, channels and leads." />
          </Card>
        ) : !data?.found ? (
          <Card className="p-8">
            <EmptyState icon={UserSearch} title="No match found"
              hint="No customer matched that search. Try an email, phone number or full name." />
          </Card>
        ) : (
          <div className="space-y-6">
            <Card className="p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="text-xl font-bold" style={{ color: INK }}>{p.name || "Unknown"}</div>
                  <div className="mt-2 flex flex-wrap gap-4 text-sm" style={{ color: SUB }}>
                    {p.email && <span className="inline-flex items-center gap-1.5"><Mail className="h-4 w-4" />{p.email}</span>}
                    {p.phone && <span className="inline-flex items-center gap-1.5"><Phone className="h-4 w-4" />{p.phone}</span>}
                    {p.company && <span className="inline-flex items-center gap-1.5"><Building2 className="h-4 w-4" />{p.company}</span>}
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {p.lead_status && <Badge tone="indigo">{p.lead_status}</Badge>}
                  {p.temperature && <Badge tone={TEMP[p.temperature] || "slate"}>{p.temperature}</Badge>}
                  {typeof p.lead_score === "number" && <Badge tone="blue">Score {p.lead_score}</Badge>}
                </div>
              </div>
              <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div>
                  <div className="text-2xl font-bold" style={{ color: INK }}>{stats.conversations ?? 0}</div>
                  <div className="text-xs" style={{ color: SUB }}>Conversations</div>
                </div>
                <div>
                  <div className="text-2xl font-bold" style={{ color: INK }}>{(stats.channels || []).length}</div>
                  <div className="text-xs" style={{ color: SUB }}>Channels</div>
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: INK }}>{timeAgo(stats.first_seen)}</div>
                  <div className="text-xs" style={{ color: SUB }}>First seen</div>
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: INK }}>{timeAgo(stats.last_seen)}</div>
                  <div className="text-xs" style={{ color: SUB }}>Last seen</div>
                </div>
              </div>
              {(stats.channels || []).length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {stats.channels.map((c) => <Badge key={c} tone="slate">{c}</Badge>)}
                </div>
              )}
            </Card>

            <Card className="p-6">
              <SectionTitle title="Journey timeline" subtitle="Every touchpoint, newest first" />
              <div className="mt-4 space-y-3">
                {(data.timeline || []).length === 0 ? (
                  <EmptyState icon={Clock} title="No activity yet" hint="This customer has no recorded touchpoints." />
                ) : (
                  data.timeline.map((ev, i) => (
                    <div key={i} className="flex items-start gap-3 rounded-xl border p-4" style={{ borderColor: LINE }}>
                      <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg" style={{ background: "#EFF4FF" }}>
                        <MessagesSquare className="h-4 w-4" style={{ color: BRAND }} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold" style={{ color: INK }}>{ev.title}</span>
                          <Badge tone="slate">{ev.channel}</Badge>
                        </div>
                        <div className="mt-0.5 flex items-center gap-3 text-xs" style={{ color: SUB }}>
                          <span>{timeAgo(ev.at)}</span>
                          {ev.status && <span>· {ev.status}</span>}
                          {ev.duration_seconds ? <span>· {ev.duration_seconds}s</span> : null}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
