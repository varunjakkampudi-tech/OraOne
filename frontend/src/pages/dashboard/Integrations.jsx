import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Plug,
  Mail,
  MessageCircle,
  MessageSquare,
  Database,
  Activity,
  XCircle,
  X,
  RefreshCw,
  Clock,
  Cloud,
  BookOpen,
  Github,
  Sparkles,
  Loader2,
  Folder,
  FileText,
  ChevronRight,
  ArrowLeft,
  SlidersHorizontal,
  CheckSquare,
  Square,
  Trash2,
  FolderTree,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { PageHeader, GhostButton } from "@/components/dashboard/kit";
import { BrandIcon, hasBrandIcon } from "@/components/dashboard/BrandIcon";

/* Map backend lucide icon names → components. */
const ICONS = {
  Mail,
  MessageSquare,
  MessageCircle,
  Database,
  Cloud,
  BookOpen,
  Github,
  Activity,
  Plug,
};

const CATEGORY_LABELS = {
  all: "All",
  communication: "Communication",
  documents: "Document Platforms",
  documentation: "Documentation",
  development: "Development",
  crm: "CRM & Business",
};

const CATEGORY_ORDER = ["all", "communication", "documents", "documentation", "development", "crm"];

function iconFor(name) {
  return ICONS[name] || Plug;
}

/* Prefer a real brand logo (simple-icons); fall back to the lucide glyph. */
function ProviderGlyph({ entry, size = 20 }) {
  const provider = entry.catalog.provider;
  if (hasBrandIcon(provider)) {
    return <BrandIcon provider={provider} size={size} />;
  }
  const Icon = iconFor(entry.catalog.icon);
  return <Icon size={size} style={{ color: entry.catalog.color }} />;
}

export default function Integrations() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("all");
  const [selected, setSelected] = useState(null); // provider key
  const [busy, setBusy] = useState({}); // provider → bool

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/integrations");
      setEntries(data.items || []);
    } catch {
      // An unseeded workspace can 404 here — show the empty catalog rather than
      // an error toast.
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Handle the OAuth round-trip: the provider callback bounces the browser
  // back here with ?connected=<provider> or ?error=<reason>.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const connected = params.get("connected");
    const error = params.get("error");
    if (!connected && !error) return;
    if (connected) {
      toast.success("Connected — start a sync to import documents.");
    } else if (error) {
      const labels = {
        invalid_state: "Authorization expired — please try connecting again.",
        token_exchange_failed: "Google rejected the authorization. Please retry.",
        missing_code: "Authorization was cancelled.",
        access_denied: "Authorization was cancelled.",
      };
      toast.error(labels[error] || `Connection failed (${error}).`);
    }
    // Strip the query params so a refresh doesn't re-fire the toast.
    window.history.replaceState({}, "", window.location.pathname);
    load();
  }, [load]);

  const setProviderBusy = (provider, v) =>
    setBusy((p) => ({ ...p, [provider]: v }));

  const connect = async (provider) => {
    setProviderBusy(provider, true);
    try {
      const { data } = await api.post("/integrations/connect", { provider });
      if (data.authorize_url) {
        window.location.href = data.authorize_url;
        return;
      }
      toast.success("Connected");
      await load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Connection failed");
    } finally {
      setProviderBusy(provider, false);
    }
  };

  const sync = async (integration, provider) => {
    if (!integration) return;
    setProviderBusy(provider, true);
    try {
      await api.post(`/integrations/${integration.id}/sync`);
      toast.success("Sync started — documents will appear in your Knowledge Base shortly.");
      // Give the background task a moment, then refresh status.
      setTimeout(load, 2500);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Sync failed");
    } finally {
      setProviderBusy(provider, false);
    }
  };

  const disconnect = async (integration, provider, name) => {
    if (!integration) return;
    if (!window.confirm(`Disconnect ${name}? Synced documents will be removed from your Knowledge Base.`)) return;
    setProviderBusy(provider, true);
    try {
      const { data } = await api.delete(`/integrations/${integration.id}`);
      toast.success(`Disconnected · ${data.documents_removed ?? 0} document(s) removed`);
      setSelected(null);
      await load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Disconnect failed");
    } finally {
      setProviderBusy(provider, false);
    }
  };

  const categories = useMemo(() => {
    const present = new Set(entries.map((e) => e.catalog.category));
    return CATEGORY_ORDER.filter((c) => c === "all" || present.has(c));
  }, [entries]);

  const list = useMemo(() => {
    const s = q.trim().toLowerCase();
    return entries.filter((e) => {
      if (cat !== "all" && e.catalog.category !== cat) return false;
      if (
        s &&
        !e.catalog.name.toLowerCase().includes(s) &&
        !e.catalog.description.toLowerCase().includes(s)
      )
        return false;
      return true;
    });
  }, [entries, q, cat]);

  const connected = useMemo(
    () => entries.filter((e) => e.integration && e.integration.status !== "disconnected"),
    [entries]
  );

  const selectedEntry = entries.find((e) => e.catalog.provider === selected) || null;

  return (
    <div className="space-y-8" data-testid="integrations-dashboard">
      {/* Header */}
      <PageHeader
        eyebrow="Integrations"
        icon={Plug}
        title="The AI layer over your business apps."
        subtitle="Connect your tools, sync their content into your Knowledge Base, and let AI answer from everything."
        actions={
          <GhostButton onClick={load} data-testid="refresh-status">
            <RefreshCw size={13} /> Refresh
          </GhostButton>
        }
      />

      {/* Connected health grid */}
      {connected.length > 0 && (
        <Section title="Connected" subtitle={`${connected.length} active integration(s)`} icon={Activity}>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="health-grid">
            {connected.map((e) => {
              return (
                <div
                  key={e.catalog.provider}
                  className="p-4 rounded-2xl border border-[#E7EAF1] bg-white shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_-12px_rgba(16,24,40,0.10)] hover:shadow-premium transition-all cursor-pointer"
                  onClick={() => setSelected(e.catalog.provider)}
                  data-testid={`health-${e.catalog.provider}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="size-9 rounded-xl grid place-items-center bg-[#F5F7FB] ring-1 ring-[#EEF0F5]">
                      <ProviderGlyph entry={e} size={16} />
                    </span>
                    <StatusPill status={e.integration.status} />
                  </div>
                  <p className="mt-3 text-[14px] font-semibold text-[#0F172A]">{e.catalog.name}</p>
                  <p className="text-[11.5px] text-[#64748B] mt-0.5 flex items-center gap-1">
                    <Clock size={10} /> {e.integration.last_synced_at ? `Synced ${timeAgo(e.integration.last_synced_at)}` : "Not synced yet"}
                  </p>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* Marketplace */}
      <Section
        title="Integration Marketplace"
        subtitle={`${entries.length} integrations · ${connected.length} connected`}
        icon={Plug}
      >
        <div className="rounded-2xl border border-[#E2E8F0] bg-white p-4 sm:p-5">
          <div className="flex flex-wrap items-center gap-3 mb-5">
            <div className="relative flex-1 min-w-[220px]">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
              <input
                type="text"
                type="text"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search integrations…"
                data-testid="int-search"
                className="w-full pl-9 pr-3 py-2 rounded-lg border border-[#E2E8F0] text-sm placeholder:text-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10"
              />
            </div>
            <div className="flex flex-wrap gap-1.5">
              {categories.map((c) => (
                <button
                  key={c}
                  onClick={() => setCat(c)}
                  data-testid={`int-cat-${c}`}
                  className={`px-3 py-1.5 rounded-full text-[12px] font-semibold border transition-colors ${
                    cat === c
                      ? "border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]"
                      : "border-[#E2E8F0] bg-white text-[#475569] hover:border-[#2563EB] hover:text-[#2563EB]"
                  }`}
                >
                  {CATEGORY_LABELS[c] || c}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="py-16 grid place-items-center text-[#94A3B8]">
              <Loader2 size={22} className="animate-spin" />
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="int-grid">
              {list.map((e) => {
                const isConnected = e.integration && e.integration.status !== "disconnected";
                return (
                  <motion.button
                    key={e.catalog.provider}
                    onClick={() => setSelected(e.catalog.provider)}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    data-testid={`int-card-${e.catalog.provider}`}
                    className="text-left p-5 rounded-2xl border border-[#E7EAF1] bg-white shadow-[0_1px_2px_rgba(16,24,40,0.04),0_8px_24px_-12px_rgba(16,24,40,0.10)] hover:border-[#2563EB]/40 hover:shadow-premium transition-all relative"
                  >
                    {!e.catalog.available && (
                      <span className="absolute top-3 right-3 text-[10px] font-bold tracking-wider text-[#92400E] bg-[#FEF3C7] px-1.5 py-0.5 rounded-full">
                        DEMO MODE
                      </span>
                    )}
                    <div className="flex items-center justify-between">
                      <span className="size-11 rounded-xl grid place-items-center bg-[#F5F7FB] ring-1 ring-[#EEF0F5]">
                        <ProviderGlyph entry={e} size={22} />
                      </span>
                      <StatusPill status={isConnected ? e.integration.status : "disconnected"} />
                    </div>
                    <p className="mt-3 text-[14.5px] font-semibold text-[#0F172A]">{e.catalog.name}</p>
                    <p className="text-[10.5px] text-[#94A3B8] uppercase tracking-wider font-bold">
                      {CATEGORY_LABELS[e.catalog.category] || e.catalog.category}
                    </p>
                    <p className="mt-2 text-[12.5px] text-[#64748B] leading-snug">{e.catalog.description}</p>
                  </motion.button>
                );
              })}
              {list.length === 0 && (
                <div className="col-span-full py-10 flex flex-col items-center justify-center text-center" data-testid="int-empty-state">
                  <div className="size-14 rounded-full grid place-items-center bg-[#EFF6FF]">
                    <Plug size={26} className="text-[#2563EB]" />
                  </div>
                  <p className="mt-4 text-[16px] font-semibold text-[#0F172A]">
                    {q ? "No matches found" : "No integrations available yet"}
                  </p>
                  <p className="mt-1 text-sm text-[#475569] max-w-sm">
                    {q
                      ? "Try a different search term to find the app you're looking for."
                      : "Connect your first app to sync its content into your Knowledge Base."}
                  </p>
                  {q ? (
                    <button
                      onClick={() => setQ("")}
                      data-testid="int-empty-clear"
                      className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-full border border-[#E2E8F0] bg-white text-[#334155] text-sm font-semibold hover:border-[#2563EB] hover:text-[#2563EB] transition-colors"
                    >
                      Clear search
                    </button>
                  ) : (
                    <button
                      onClick={load}
                      data-testid="int-empty-refresh"
                      className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#2563EB] text-white text-sm font-semibold shadow-sm hover:bg-[#1D4ED8] transition-colors"
                    >
                      <RefreshCw size={15} /> Refresh marketplace
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </Section>

      {/* Detail drawer */}
      <AnimatePresence>
        {selectedEntry && (
          <DetailDrawer
            entry={selectedEntry}
            busy={!!busy[selectedEntry.catalog.provider]}
            onClose={() => setSelected(null)}
            onConnect={() => connect(selectedEntry.catalog.provider)}
            onSync={() => sync(selectedEntry.integration, selectedEntry.catalog.provider)}
            onDisconnect={() =>
              disconnect(selectedEntry.integration, selectedEntry.catalog.provider, selectedEntry.catalog.name)
            }
          />
        )}
      </AnimatePresence>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────── */
function DetailDrawer({ entry, busy, onClose, onConnect, onSync, onDisconnect }) {
  const { catalog, integration } = entry;
  const isConnected = integration && integration.status !== "disconnected";
  const [logs, setLogs] = useState([]);
  const [items, setItems] = useState([]);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [removalSel, setRemovalSel] = useState(() => new Set());
  const [browseOpen, setBrowseOpen] = useState(false);
  const [removing, setRemoving] = useState(false);

  const loadItems = useCallback(async () => {
    if (!integration) return;
    setItemsLoading(true);
    try {
      const { data } = await api.get(`/integrations/${integration.id}/items`, {
        params: { limit: 500 },
      });
      setItems(data.items || []);
    } catch {
      /* manifest may be empty before first selection */
    } finally {
      setItemsLoading(false);
    }
  }, [integration]);

  useEffect(() => {
    let active = true;
    if (integration) {
      api
        .get(`/integrations/${integration.id}/logs`, { params: { limit: 20 } })
        .then(({ data }) => active && setLogs(data.items || []))
        .catch(() => {});
      loadItems();
    }
    return () => {
      active = false;
    };
  }, [integration, loadItems]);

  const toggleRemoval = (extId) =>
    setRemovalSel((prev) => {
      const next = new Set(prev);
      next.has(extId) ? next.delete(extId) : next.add(extId);
      return next;
    });

  const removeSelected = async () => {
    if (!integration || removalSel.size === 0) return;
    if (!window.confirm(`Remove ${removalSel.size} item(s) from your Knowledge Base?`)) return;
    setRemoving(true);
    try {
      const { data } = await api.post(`/integrations/${integration.id}/items/remove`, {
        external_ids: Array.from(removalSel),
      });
      toast.success(`Removed · ${data.documents_removed ?? 0} document(s) purged`);
      setRemovalSel(new Set());
      await loadItems();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Remove failed");
    } finally {
      setRemoving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-50 bg-[#0F172A]/50 backdrop-blur-sm"
      data-testid="int-detail-drawer"
    >
      <motion.div
        initial={{ x: "100%" }}
        animate={{ x: 0 }}
        exit={{ x: "100%" }}
        transition={{ type: "tween", duration: 0.25 }}
        onClick={(e) => e.stopPropagation()}
        className="absolute top-0 right-0 h-full w-full max-w-xl bg-white shadow-2xl overflow-y-auto"
      >
        <div className="p-6 border-b border-[#E2E8F0]">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <span className="size-12 rounded-2xl grid place-items-center bg-[#F5F7FB] ring-1 ring-[#EEF0F5]">
                <ProviderGlyph entry={entry} size={24} />
              </span>
              <div>
                <h3 className="text-lg font-bold text-[#0F172A]">{catalog.name}</h3>
                <p className="text-[11px] text-[#94A3B8] uppercase tracking-wider font-bold">
                  {CATEGORY_LABELS[catalog.category] || catalog.category}
                </p>
              </div>
            </div>
            <button onClick={onClose} aria-label="Close panel" className="text-[#94A3B8] hover:text-[#0F172A]" data-testid="int-detail-close">
              <X size={18} />
            </button>
          </div>
          <StatusPill status={isConnected ? integration.status : "disconnected"} large />
        </div>

        <div className="p-6 space-y-6">
          <div>
            <p className="text-[11px] font-bold tracking-[0.2em] text-[#2563EB] mb-2">OVERVIEW</p>
            <p className="text-[13.5px] text-[#475569] leading-relaxed">{catalog.description}</p>
            {!catalog.available && (
              <p className="mt-3 text-[12px] text-[#92400E] bg-[#FEF3C7] rounded-lg px-3 py-2">
                Runs in demo mode — connecting imports a small sample document set so you can test
                end-to-end retrieval. Real OAuth ships next.
              </p>
            )}
          </div>

          {isConnected && (
            <div className="grid grid-cols-2 gap-3">
              <Stat label="Account" value={integration.external_account || "—"} />
              <Stat label="Last sync" value={integration.last_synced_at ? timeAgo(integration.last_synced_at) : "Never"} />
              <Stat label="Schedule" value={integration.sync_schedule} />
              <Stat label="Mode" value={integration.connection_type} />
            </div>
          )}

          {integration && integration.last_error && (
            <p className="text-[12px] text-[#B91C1C] bg-[#FEE2E2] rounded-lg px-3 py-2">
              {integration.last_error}
            </p>
          )}

          {/* Actions */}
          {!isConnected ? (
            <button
              onClick={onConnect}
              disabled={busy}
              data-testid="int-connect-cta"
              className="w-full px-4 py-3 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-60 text-white text-sm font-semibold inline-flex items-center justify-center gap-1.5"
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Plug size={14} />}
              Connect {catalog.name}
            </button>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                onClick={() => setBrowseOpen(true)}
                disabled={busy}
                data-testid="int-browse"
                className="px-3 py-2.5 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-60 text-white text-[13px] font-semibold inline-flex items-center justify-center gap-1.5"
              >
                <FolderTree size={13} /> Browse Files
              </button>
              <button
                onClick={onSync}
                disabled={busy}
                data-testid="int-sync"
                className="px-3 py-2.5 rounded-xl border border-[#E2E8F0] hover:bg-[#F8FAFC] text-[#0F172A] text-[13px] font-semibold inline-flex items-center justify-center gap-1.5"
              >
                {busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />} Sync Now
              </button>
              <button
                onClick={removeSelected}
                disabled={removing || removalSel.size === 0}
                data-testid="int-remove-selected"
                className="px-3 py-2.5 rounded-xl border border-[#E2E8F0] hover:bg-[#F8FAFC] disabled:opacity-50 text-[#0F172A] text-[13px] font-semibold inline-flex items-center justify-center gap-1.5"
              >
                {removing ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                Remove{removalSel.size > 0 ? ` (${removalSel.size})` : ""}
              </button>
              <button
                onClick={onDisconnect}
                disabled={busy}
                data-testid="int-disconnect"
                className="px-3 py-2.5 rounded-xl border border-[#FEE2E2] bg-[#FEF2F2] hover:bg-[#FEE2E2] text-[#B91C1C] text-[13px] font-semibold inline-flex items-center justify-center gap-1.5"
              >
                <XCircle size={13} /> Disconnect
              </button>
            </div>
          )}

          {/* Synced content manifest */}
          {isConnected && (
            <div data-testid="int-synced-content">
              <div className="flex items-center justify-between mb-3">
                <p className="text-[11px] font-bold tracking-[0.2em] text-[#2563EB]">
                  SYNCED CONTENT
                </p>
                <span className="text-[11px] text-[#94A3B8]">
                  {items.length} item(s)
                </span>
              </div>
              {itemsLoading ? (
                <div className="py-6 grid place-items-center text-[#94A3B8]">
                  <Loader2 size={18} className="animate-spin" />
                </div>
              ) : items.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#E2E8F0] px-4 py-6 text-center">
                  <p className="text-[12.5px] text-[#64748B]">
                    Nothing selected yet. Click <b>Browse Files</b> to choose folders or
                    files to sync.
                  </p>
                </div>
              ) : (
                <div className="rounded-xl border border-[#E2E8F0] divide-y divide-[#F1F5F9] max-h-72 overflow-y-auto">
                  {items.map((it) => {
                    const ItIcon = it.is_folder ? Folder : FileText;
                    const checked = removalSel.has(it.external_id);
                    return (
                      <div
                        key={it.id}
                        className="flex items-center gap-2.5 px-3 py-2.5 hover:bg-[#F8FAFC]"
                      >
                        <button
                          onClick={() => toggleRemoval(it.external_id)}
                          className="flex-shrink-0 text-[#2563EB]"
                          data-testid={`synced-check-${it.external_id}`}
                        >
                          {checked ? <CheckSquare size={16} /> : <Square size={16} className="text-[#CBD5E1]" />}
                        </button>
                        <ItIcon size={15} className={it.is_folder ? "text-[#2563EB]" : "text-[#64748B]"} />
                        <div className="min-w-0 flex-1">
                          <p className="text-[12.5px] font-medium text-[#0F172A] truncate">{it.name}</p>
                          {it.path && (
                            <p className="text-[10.5px] text-[#94A3B8] truncate">{it.path}</p>
                          )}
                        </div>
                        <SyncedStatusPill status={it.status} />
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Sync logs */}
          {isConnected && logs.length > 0 && (
            <div>
              <p className="text-[11px] font-bold tracking-[0.2em] text-[#2563EB] mb-3">RECENT ACTIVITY</p>
              <div className="space-y-1.5">
                {logs.map((l) => (
                  <div key={l.id} className="flex items-start gap-2 text-[12.5px]">
                    <span className={`mt-1 size-1.5 rounded-full flex-shrink-0 ${l.level === "error" ? "bg-[#DC2626]" : l.level === "warning" ? "bg-[#F59E0B]" : "bg-[#16A34A]"}`} />
                    <div className="min-w-0">
                      <span className="font-semibold text-[#0F172A]">{l.event}</span>
                      {l.message && <span className="text-[#64748B]"> — {l.message}</span>}
                      <span className="block text-[10.5px] text-[#94A3B8]">{timeAgo(l.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </motion.div>

      <AnimatePresence>
        {browseOpen && integration && (
          <BrowseModal
            integrationId={integration.id}
            providerName={catalog.name}
            onClose={() => setBrowseOpen(false)}
            onSaved={async ({ triggerSync }) => {
              setBrowseOpen(false);
              await loadItems();
              if (triggerSync) onSync();
            }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ──────────────────────────────────────────────────────────────────── */
function SyncedStatusPill({ status }) {
  const map = {
    synced: { bg: "#DCFCE7", text: "#15803D", label: "Synced" },
    pending: { bg: "#FEF9C3", text: "#A16207", label: "Pending" },
    failed: { bg: "#FEE2E2", text: "#B91C1C", label: "Failed" },
    skipped: { bg: "#F1F5F9", text: "#64748B", label: "Skipped" },
    removed: { bg: "#F1F5F9", text: "#94A3B8", label: "Removed" },
  };
  const s = map[status] || map.pending;
  return (
    <span
      className="flex-shrink-0 px-2 py-0.5 rounded-full text-[10px] font-semibold"
      style={{ background: s.bg, color: s.text }}
    >
      {s.label}
    </span>
  );
}

/* ──────────────────────────────────────────────────────────────────── */
const FILE_TYPE_OPTIONS = [
  { key: "pdf", label: "PDF" },
  { key: "gdoc", label: "Google Docs" },
  { key: "docx", label: "Word" },
  { key: "gsheet", label: "Sheets" },
  { key: "csv", label: "CSV" },
  { key: "txt", label: "Text" },
  { key: "md", label: "Markdown" },
];

const SYNC_MODES = [
  { key: "quick", label: "Quick", hint: "Recent files (last 30 days)" },
  { key: "folder", label: "Folders", hint: "Pick specific folders & files" },
  { key: "full", label: "Full Drive", hint: "Everything (use with care)" },
];

function BrowseModal({ integrationId, providerName, onClose, onSaved }) {
  const [mode, setMode] = useState("folder");
  const [stack, setStack] = useState([{ id: null, name: providerName }]);
  const [tab, setTab] = useState("browse"); // browse | recent
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [folders, setFolders] = useState(() => new Map()); // id → ref
  const [files, setFiles] = useState(() => new Map());
  const [showFilters, setShowFilters] = useState(false);
  const [options, setOptions] = useState({
    file_types: null,
    ignore_images: true,
    ignore_videos: true,
    max_size_mb: 100,
    ignore_trash: true,
    ignore_shared: false,
  });
  const [step, setStep] = useState("select"); // select | confirm
  const [saving, setSaving] = useState(false);

  const current = stack[stack.length - 1];

  const fetchBrowse = useCallback(
    async ({ parent, q, recent }) => {
      setLoading(true);
      try {
        const { data: res } = await api.get(`/integrations/${integrationId}/browse`, {
          params: { parent: parent ?? undefined, q: q || undefined, recent: recent || undefined },
        });
        setData(res.items || []);
      } catch (err) {
        toast.error(formatApiError(err.response?.data?.detail) || "Browse failed");
        setData([]);
      } finally {
        setLoading(false);
      }
    },
    [integrationId]
  );

  useEffect(() => {
    if (tab === "recent") {
      fetchBrowse({ recent: true });
    } else {
      fetchBrowse({ parent: current.id });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, current.id]);

  const runSearch = () => {
    if (search.trim()) fetchBrowse({ q: search.trim() });
    else fetchBrowse({ parent: current.id });
  };

  const openFolder = (item) =>
    setStack((s) => [...s, { id: item.external_id, name: item.name }]);

  const goTo = (idx) => setStack((s) => s.slice(0, idx + 1));

  const toggleFolder = (item) =>
    setFolders((prev) => {
      const next = new Map(prev);
      if (next.has(item.external_id)) next.delete(item.external_id);
      else
        next.set(item.external_id, {
          external_id: item.external_id,
          name: item.name,
          path: item.path,
        });
      return next;
    });

  const toggleFile = (item) =>
    setFiles((prev) => {
      const next = new Map(prev);
      if (next.has(item.external_id)) next.delete(item.external_id);
      else
        next.set(item.external_id, {
          external_id: item.external_id,
          name: item.name,
          path: item.path,
          mime_type: item.mime_type,
        });
      return next;
    });

  const toggleFileType = (key) =>
    setOptions((o) => {
      const cur = o.file_types || [];
      const has = cur.includes(key);
      const nextArr = has ? cur.filter((k) => k !== key) : [...cur, key];
      return { ...o, file_types: nextArr.length ? nextArr : null };
    });

  const totalSelected = folders.size + files.size;

  const save = async (triggerSync) => {
    setSaving(true);
    try {
      const effectiveMode =
        mode === "full" ? "full" : mode === "quick" ? "quick" : "folder";
      await api.put(`/integrations/${integrationId}/selection`, {
        mode: effectiveMode,
        folders: Array.from(folders.values()),
        files: Array.from(files.values()),
        options: {
          ...options,
          recent_days: mode === "quick" ? 30 : null,
        },
      });
      toast.success("Selection saved");
      onSaved({ triggerSync });
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Failed to save selection");
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 z-[60] bg-[#0F172A]/60 backdrop-blur-sm grid place-items-center p-4"
      data-testid="browse-modal"
    >
      <motion.div
        initial={{ scale: 0.96, y: 10 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.96, y: 10 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl max-h-[88vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden"
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-[#E2E8F0] flex items-center justify-between">
          <div>
            <h3 className="text-[15px] font-bold text-[#0F172A]">
              {step === "select" ? "Select content to sync" : "Confirm selection"}
            </h3>
            <p className="text-[12px] text-[#64748B]">{providerName}</p>
          </div>
          <button onClick={onClose} className="text-[#94A3B8] hover:text-[#0F172A]">
            <X size={18} />
          </button>
        </div>

        {step === "select" ? (
          <>
            {/* Mode selector */}
            <div className="px-5 pt-4">
              <div className="grid grid-cols-3 gap-2">
                {SYNC_MODES.map((m) => (
                  <button
                    key={m.key}
                    onClick={() => setMode(m.key)}
                    data-testid={`browse-mode-${m.key}`}
                    className={`text-left px-3 py-2 rounded-xl border transition-colors ${
                      mode === m.key
                        ? "border-[#2563EB] bg-[#EFF6FF]"
                        : "border-[#E2E8F0] hover:border-[#2563EB]/40"
                    }`}
                  >
                    <p className="text-[12.5px] font-semibold text-[#0F172A]">{m.label}</p>
                    <p className="text-[10.5px] text-[#64748B] leading-tight mt-0.5">{m.hint}</p>
                  </button>
                ))}
              </div>
            </div>

            {mode === "full" ? (
              <div className="px-5 py-8 flex-1">
                <div className="rounded-xl border border-[#FDE68A] bg-[#FFFBEB] px-4 py-3 text-[12.5px] text-[#92400E]">
                  Full Drive sync imports <b>all</b> supported files. This may include
                  sensitive documents and increases storage/embedding costs. Filters below
                  still apply.
                </div>
                <FiltersPanel
                  options={options}
                  setOptions={setOptions}
                  toggleFileType={toggleFileType}
                  alwaysOpen
                />
              </div>
            ) : (
              <>
                {/* Tabs + search */}
                <div className="px-5 pt-3 flex items-center gap-2">
                  <div className="flex gap-1 bg-[#F1F5F9] rounded-lg p-0.5">
                    {["browse", "recent"].map((t) => (
                      <button
                        key={t}
                        onClick={() => {
                          setTab(t);
                          setSearch("");
                        }}
                        data-testid={`browse-tab-${t}`}
                        className={`px-3 py-1.5 rounded-md text-[12px] font-semibold capitalize ${
                          tab === t ? "bg-white text-[#2563EB] shadow-sm" : "text-[#64748B]"
                        }`}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                  {tab === "browse" && (
                    <div className="relative flex-1">
                      <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
                      <input
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && runSearch()}
                        placeholder="Search files…"
                        className="w-full pl-8 pr-2 py-1.5 rounded-lg border border-[#E2E8F0] text-[12.5px] focus:border-[#2563EB] focus:outline-none"
                      />
                    </div>
                  )}
                  <button
                    onClick={() => setShowFilters((v) => !v)}
                    data-testid="browse-filters-toggle"
                    className={`px-2.5 py-1.5 rounded-lg border text-[12px] font-semibold inline-flex items-center gap-1 ${
                      showFilters ? "border-[#2563EB] text-[#2563EB] bg-[#EFF6FF]" : "border-[#E2E8F0] text-[#475569]"
                    }`}
                  >
                    <SlidersHorizontal size={12} /> Filters
                  </button>
                </div>

                {/* Breadcrumb */}
                {tab === "browse" && !search && (
                  <div className="px-5 pt-2 flex items-center gap-1 text-[11.5px] text-[#64748B] flex-wrap">
                    {stack.length > 1 && (
                      <button
                        onClick={() => setStack((s) => s.slice(0, -1))}
                        className="mr-1 text-[#2563EB] inline-flex items-center"
                      >
                        <ArrowLeft size={13} />
                      </button>
                    )}
                    {stack.map((s, i) => (
                      <span key={i} className="inline-flex items-center gap-1">
                        {i > 0 && <ChevronRight size={11} className="text-[#CBD5E1]" />}
                        <button
                          onClick={() => goTo(i)}
                          className={i === stack.length - 1 ? "font-semibold text-[#0F172A]" : "hover:text-[#2563EB]"}
                        >
                          {s.name}
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                {showFilters && (
                  <div className="px-5 pt-2">
                    <FiltersPanel options={options} setOptions={setOptions} toggleFileType={toggleFileType} />
                  </div>
                )}

                {/* List */}
                <div className="flex-1 overflow-y-auto px-5 py-3 min-h-[180px]">
                  {loading ? (
                    <div className="py-10 grid place-items-center text-[#94A3B8]">
                      <Loader2 size={20} className="animate-spin" />
                    </div>
                  ) : data.length === 0 ? (
                    <div className="py-10 text-center text-[12.5px] text-[#94A3B8]">
                      No items here.
                    </div>
                  ) : (
                    <div className="space-y-1">
                      {data.map((item) => {
                        const selectedF = item.is_folder
                          ? folders.has(item.external_id)
                          : files.has(item.external_id);
                        const ItIcon = item.is_folder ? Folder : FileText;
                        return (
                          <div
                            key={item.external_id}
                            className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-[#F8FAFC] group"
                          >
                            <button
                              onClick={() =>
                                item.is_folder ? toggleFolder(item) : toggleFile(item)
                              }
                              data-testid={`browse-check-${item.external_id}`}
                              className="text-[#2563EB] flex-shrink-0"
                            >
                              {selectedF ? <CheckSquare size={16} /> : <Square size={16} className="text-[#CBD5E1]" />}
                            </button>
                            <ItIcon size={16} className={item.is_folder ? "text-[#2563EB]" : "text-[#64748B]"} />
                            <button
                              onClick={() => item.is_folder && openFolder(item)}
                              className="min-w-0 flex-1 text-left"
                              disabled={!item.is_folder}
                            >
                              <p className="text-[12.5px] font-medium text-[#0F172A] truncate">{item.name}</p>
                              {item.size != null && (
                                <p className="text-[10px] text-[#94A3B8]">{formatBytes(item.size)}</p>
                              )}
                            </button>
                            {item.is_folder && (
                              <ChevronRight
                                size={14}
                                className="text-[#CBD5E1] group-hover:text-[#94A3B8] flex-shrink-0"
                              />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Footer */}
            <div className="px-5 py-3 border-t border-[#E2E8F0] flex items-center justify-between">
              <span className="text-[12px] text-[#64748B]">
                {mode === "full"
                  ? "Full Drive"
                  : `${folders.size} folder(s) · ${files.size} file(s)`}
              </span>
              <button
                onClick={() => setStep("confirm")}
                disabled={mode !== "full" && totalSelected === 0}
                data-testid="browse-continue"
                className="px-4 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-50 text-white text-[13px] font-semibold"
              >
                Continue
              </button>
            </div>
          </>
        ) : (
          /* Confirm step */
          <div className="flex-1 overflow-y-auto px-5 py-5">
            <div className="rounded-xl border border-[#E2E8F0] divide-y divide-[#F1F5F9]">
              <ConfirmRow label="Sync strategy" value={SYNC_MODES.find((m) => m.key === mode)?.label} />
              {mode !== "full" && (
                <>
                  <ConfirmRow label="Folders selected" value={`${folders.size}`} />
                  <ConfirmRow label="Files selected" value={`${files.size}`} />
                </>
              )}
              <ConfirmRow
                label="File types"
                value={
                  options.file_types && options.file_types.length
                    ? options.file_types
                        .map((k) => FILE_TYPE_OPTIONS.find((o) => o.key === k)?.label || k)
                        .join(", ")
                    : "All supported"
                }
              />
              <ConfirmRow label="Max size" value={`${options.max_size_mb} MB`} />
              <ConfirmRow
                label="Excludes"
                value={[
                  options.ignore_images && "images",
                  options.ignore_videos && "videos",
                  options.ignore_trash && "trash",
                  options.ignore_shared && "shared",
                ]
                  .filter(Boolean)
                  .join(", ") || "none"}
              />
            </div>
            {mode !== "full" && totalSelected > 0 && (
              <div className="mt-4">
                <p className="text-[11px] font-bold tracking-[0.15em] text-[#2563EB] mb-2">SELECTED</p>
                <div className="flex flex-wrap gap-1.5">
                  {Array.from(folders.values()).map((f) => (
                    <span key={f.external_id} className="inline-flex items-center gap-1 text-[11.5px] bg-[#EFF6FF] text-[#1D4ED8] px-2 py-1 rounded-lg">
                      <Folder size={11} /> {f.name}
                    </span>
                  ))}
                  {Array.from(files.values()).map((f) => (
                    <span key={f.external_id} className="inline-flex items-center gap-1 text-[11.5px] bg-[#F1F5F9] text-[#475569] px-2 py-1 rounded-lg">
                      <FileText size={11} /> {f.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div className="mt-6 flex items-center justify-between">
              <button
                onClick={() => setStep("select")}
                className="px-4 py-2 rounded-xl border border-[#E2E8F0] hover:bg-[#F8FAFC] text-[#0F172A] text-[13px] font-semibold inline-flex items-center gap-1.5"
              >
                <ArrowLeft size={13} /> Back
              </button>
              <div className="flex gap-2">
                <button
                  onClick={() => save(false)}
                  disabled={saving}
                  className="px-4 py-2 rounded-xl border border-[#E2E8F0] hover:bg-[#F8FAFC] disabled:opacity-60 text-[#0F172A] text-[13px] font-semibold"
                >
                  Save
                </button>
                <button
                  onClick={() => save(true)}
                  disabled={saving}
                  data-testid="browse-start-sync"
                  className="px-4 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] disabled:opacity-60 text-white text-[13px] font-semibold inline-flex items-center gap-1.5"
                >
                  {saving ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                  Save & Sync
                </button>
              </div>
            </div>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}

function FiltersPanel({ options, setOptions, toggleFileType, alwaysOpen }) {
  return (
    <div className={`rounded-xl border border-[#E2E8F0] p-3 ${alwaysOpen ? "mt-4" : ""} bg-[#FAFBFC]`}>
      <p className="text-[11px] font-bold tracking-[0.15em] text-[#475569] mb-2">FILE TYPES</p>
      <div className="flex flex-wrap gap-1.5 mb-3">
        {FILE_TYPE_OPTIONS.map((o) => {
          const active = options.file_types?.includes(o.key);
          return (
            <button
              key={o.key}
              onClick={() => toggleFileType(o.key)}
              className={`px-2.5 py-1 rounded-full text-[11.5px] font-semibold border ${
                active ? "border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]" : "border-[#E2E8F0] text-[#64748B]"
              }`}
            >
              {o.label}
            </button>
          );
        })}
        {options.file_types && (
          <button
            onClick={() => setOptions((o) => ({ ...o, file_types: null }))}
            className="px-2.5 py-1 rounded-full text-[11.5px] font-semibold text-[#94A3B8]"
          >
            Clear
          </button>
        )}
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
        <ToggleRow
          label="Ignore images"
          checked={options.ignore_images}
          onChange={(v) => setOptions((o) => ({ ...o, ignore_images: v }))}
        />
        <ToggleRow
          label="Ignore videos"
          checked={options.ignore_videos}
          onChange={(v) => setOptions((o) => ({ ...o, ignore_videos: v }))}
        />
        <ToggleRow
          label="Ignore Trash"
          checked={options.ignore_trash}
          onChange={(v) => setOptions((o) => ({ ...o, ignore_trash: v }))}
        />
        <ToggleRow
          label="Ignore Shared"
          checked={options.ignore_shared}
          onChange={(v) => setOptions((o) => ({ ...o, ignore_shared: v }))}
        />
      </div>
      <div className="mt-3 flex items-center gap-2">
        <span className="text-[11.5px] text-[#475569] font-medium">Max file size</span>
        <input
          type="number"
          min={1}
          value={options.max_size_mb ?? ""}
          onChange={(e) =>
            setOptions((o) => ({ ...o, max_size_mb: Number(e.target.value) || null }))
          }
          className="w-16 px-2 py-1 rounded-lg border border-[#E2E8F0] text-[12px] focus:border-[#2563EB] focus:outline-none"
        />
        <span className="text-[11.5px] text-[#64748B]">MB</span>
      </div>
    </div>
  );
}

function ToggleRow({ label, checked, onChange }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className="flex items-center gap-2 text-left"
      type="button"
    >
      {checked ? (
        <CheckSquare size={15} className="text-[#2563EB] flex-shrink-0" />
      ) : (
        <Square size={15} className="text-[#CBD5E1] flex-shrink-0" />
      )}
      <span className="text-[12px] text-[#475569]">{label}</span>
    </button>
  );
}

function ConfirmRow({ label, value }) {
  return (
    <div className="flex items-center justify-between px-3 py-2.5">
      <span className="text-[12px] text-[#64748B]">{label}</span>
      <span className="text-[12.5px] font-semibold text-[#0F172A] text-right max-w-[60%] truncate">
        {value}
      </span>
    </div>
  );
}

function formatBytes(n) {
  if (n == null) return "";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function Stat({ label, value }) {
  return (
    <div className="px-3 py-2.5 rounded-xl border border-[#E2E8F0]">
      <p className="text-[10.5px] text-[#94A3B8] uppercase tracking-wider font-bold">{label}</p>
      <p className="text-[13px] font-semibold text-[#0F172A] truncate capitalize">{value}</p>
    </div>
  );
}

function StatusPill({ status, large }) {
  const map = {
    connected: { bg: "#DCFCE7", dot: "#16A34A", text: "#15803D", label: "Connected" },
    syncing: { bg: "#DBEAFE", dot: "#2563EB", text: "#1D4ED8", label: "Syncing" },
    error: { bg: "#FEE2E2", dot: "#DC2626", text: "#B91C1C", label: "Error" },
    disconnected: { bg: "#F1F5F9", dot: "#94A3B8", text: "#64748B", label: "Not Connected" },
  };
  const s = map[status] || map.disconnected;
  return (
    <span
      className={`inline-flex items-center gap-1 ${large ? "px-2.5 py-1 text-[12px]" : "px-2 py-0.5 text-[10.5px]"} rounded-full font-semibold`}
      style={{ background: s.bg, color: s.text }}
    >
      <span className="size-1.5 rounded-full" style={{ background: s.dot }} />
      {s.label}
    </span>
  );
}

function Section({ title, subtitle, icon: Icon, children }) {
  return (
    <section>
      <div className="flex items-center gap-2.5 mb-4">
        {Icon && (
          <span className="size-8 rounded-lg bg-[#EFF6FF] grid place-items-center">
            <Icon size={15} className="text-[#2563EB]" />
          </span>
        )}
        <div>
          <h2 className="text-[16px] font-bold text-[#0F172A]">{title}</h2>
          {subtitle && <p className="text-[12px] text-[#94A3B8]">{subtitle}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

function timeAgo(iso) {
  const d = new Date(iso);
  const secs = Math.floor((Date.now() - d.getTime()) / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
