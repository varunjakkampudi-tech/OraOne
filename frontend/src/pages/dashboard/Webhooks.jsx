import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Webhook as WebhookIcon,
  Loader2,
  RefreshCw,
  Plus,
  Copy,
  Check,
  Trash2,
  ShieldCheck,
  X,
  Send,
  RotateCcw,
  Pause,
  Play,
  ChevronDown,
  CircleCheck,
  CircleX,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { usePermissions } from "@/hooks/usePermissions";

function fmtRelative(value) {
  if (!value) return "Never";
  const then = new Date(value).getTime();
  const diff = Date.now() - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

const STATUS_STYLES = {
  active: "bg-[#DCFCE7] text-[#16A34A]",
  paused: "bg-[#FEF3C7] text-[#B45309]",
  disabled: "bg-[#FEE2E2] text-[#DC2626]",
};

function StatusBadge({ status }) {
  const cls = STATUS_STYLES[status] || "bg-[#F1F5F9] text-[#475569]";
  return (
    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold capitalize ${cls}`}>
      {status}
    </span>
  );
}

function EventChip({ children }) {
  return (
    <span className="rounded-md bg-[#EEF2FF] px-2 py-0.5 font-mono text-[11px] font-medium text-[#4F46E5]">
      {children}
    </span>
  );
}

function EventPicker({ events, selected, toggle }) {
  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {events.map((e) => {
        const on = selected.includes(e.event);
        return (
          <button
            key={e.event}
            type="button"
            onClick={() => toggle(e.event)}
            data-testid={`event-${e.event}`}
            className={`flex items-start justify-between gap-2 rounded-xl border px-3 py-2 text-left text-sm transition ${
              on ? "border-[#4F46E5] bg-[#EEF2FF]" : "border-[#E2E8F0] bg-white hover:bg-[#F8FAFC]"
            }`}
          >
            <span className="min-w-0">
              <span className="block font-mono text-[12px] font-medium text-[#0F172A]">{e.event}</span>
              <span className="mt-0.5 block text-[11px] text-[#94A3B8]">{e.description}</span>
            </span>
            {on && <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#4F46E5]" />}
          </button>
        );
      })}
    </div>
  );
}

function CreateWebhookModal({ events, onClose, onCreated }) {
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const toggle = (e) =>
    setSelected((prev) => (prev.includes(e) ? prev.filter((s) => s !== e) : [...prev, e]));

  const submit = async () => {
    const u = url.trim();
    if (!/^https?:\/\//i.test(u)) {
      toast.error("Enter a valid http(s) URL.");
      return;
    }
    if (!selected.length) {
      toast.error("Select at least one event.");
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post("/webhooks", {
        url: u,
        events: selected,
        description: description.trim() || null,
      });
      onCreated(data);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-bold text-[#0F172A]">Add webhook endpoint</h2>
            <p className="text-sm text-[#64748B]">We'll POST signed events to your URL.</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1 text-[#94A3B8] hover:bg-[#F1F5F9]">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-5 space-y-5">
          <div>
            <label className="text-sm font-medium text-[#334155]">Endpoint URL</label>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              data-testid="webhook-url"
              placeholder="https://example.com/webhooks/oraone"
              className="mt-1 w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-[#334155]">Description (optional)</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Production CRM sync"
              className="mt-1 w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#4F46E5]"
            />
          </div>
          <div>
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-[#334155]">Events</label>
              <span className="text-[11px] text-[#94A3B8]">{selected.length} selected</span>
            </div>
            <div className="mt-2">
              <EventPicker events={events} selected={selected} toggle={toggle} />
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-xl border border-[#E2E8F0] px-4 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC]">
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={submitting}
            data-testid="webhook-create-submit"
            className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA] disabled:opacity-60"
          >
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Create endpoint
          </button>
        </div>
      </motion.div>
    </div>
  );
}

function RevealSecretModal({ secret, onClose }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(secret);
      setCopied(true);
      toast.success("Signing secret copied");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Couldn't copy — select and copy manually.");
    }
  };
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl"
      >
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-[#DCFCE7] text-[#16A34A]">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[#0F172A]">Signing secret</h2>
            <p className="text-sm text-[#64748B]">Store it now — it won't be shown again.</p>
          </div>
        </div>
        <div className="mt-5 flex items-stretch gap-2">
          <code data-testid="webhook-secret" className="flex-1 break-all rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-3 font-mono text-xs text-[#0F172A]">
            {secret}
          </code>
          <button onClick={copy} className="shrink-0 rounded-xl bg-[#4F46E5] px-3 text-white hover:bg-[#4338CA]">
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </button>
        </div>
        <div className="mt-4 rounded-xl border border-[#E2E8F0] bg-[#0F172A] p-4 text-xs text-[#CBD5E1]">
          <p className="mb-2 text-[#94A3B8]">Verify the signature header</p>
          <pre className="overflow-x-auto whitespace-pre-wrap font-mono">
{`X-OraOne-Signature: t=<ts>,v1=<hmac_sha256>
// signed_payload = "{t}.{raw_body}"
// expected = HMAC_SHA256(secret, signed_payload)`}
          </pre>
        </div>
        <div className="mt-6 flex justify-end">
          <button onClick={onClose} data-testid="webhook-secret-done" className="rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA]">
            Done
          </button>
        </div>
      </motion.div>
    </div>
  );
}

function DeliveriesRow({ endpointId }) {
  const [loading, setLoading] = useState(true);
  const [deliveries, setDeliveries] = useState([]);

  useEffect(() => {
    let on = true;
    setLoading(true);
    api
      .get(`/webhooks/${endpointId}/deliveries`, { params: { limit: 20 } })
      .then(({ data }) => on && setDeliveries(Array.isArray(data) ? data : []))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => on && setLoading(false));
    return () => {
      on = false;
    };
  }, [endpointId]);

  if (loading) {
    return (
      <div className="grid place-items-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-[#4F46E5]" />
      </div>
    );
  }
  if (!deliveries.length) {
    return <p className="py-6 text-center text-sm text-[#94A3B8]">No deliveries yet. Send a test to try it out.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#E2E8F0] text-left text-[11px] uppercase tracking-wide text-[#94A3B8]">
            <th className="py-2 pr-4 font-semibold">Event</th>
            <th className="py-2 pr-4 font-semibold">Result</th>
            <th className="py-2 pr-4 font-semibold">Status</th>
            <th className="py-2 pr-4 font-semibold">Attempts</th>
            <th className="py-2 pr-4 font-semibold">When</th>
          </tr>
        </thead>
        <tbody>
          {deliveries.map((d) => (
            <tr key={d.id} className="border-b border-[#F1F5F9] last:border-0">
              <td className="py-2.5 pr-4 font-mono text-[12px] text-[#475569]">{d.event}</td>
              <td className="py-2.5 pr-4">
                {d.success ? (
                  <span className="inline-flex items-center gap-1 text-[#16A34A]">
                    <CircleCheck className="h-4 w-4" /> Delivered
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[#DC2626]">
                    <CircleX className="h-4 w-4" /> Failed
                  </span>
                )}
              </td>
              <td className="py-2.5 pr-4 tabular-nums text-[#475569]">{d.status_code ?? "—"}</td>
              <td className="py-2.5 pr-4 tabular-nums text-[#475569]">{d.attempts}</td>
              <td className="py-2.5 pr-4 text-[#64748B]">{fmtRelative(d.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Webhooks() {
  const { can } = usePermissions();
  const [endpoints, setEndpoints] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [secret, setSecret] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const canManage = can("apikeys.manage");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/webhooks");
      setEndpoints(data.webhooks || []);
      setEvents(data.events || []);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onCreated = (payload) => {
    setShowCreate(false);
    setSecret(payload.secret);
    load();
  };

  const sendTest = async (ep) => {
    setBusyId(ep.id);
    try {
      const { data } = await api.post(`/webhooks/${ep.id}/test`);
      if (data.success) toast.success("Test delivered successfully");
      else toast.error(`Test failed${data.status_code ? ` (HTTP ${data.status_code})` : ""}`);
      setExpanded(ep.id);
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusyId(null);
    }
  };

  const toggleStatus = async (ep) => {
    const next = ep.status === "active" ? "paused" : "active";
    setBusyId(ep.id);
    try {
      await api.patch(`/webhooks/${ep.id}`, { status: next });
      toast.success(next === "active" ? "Endpoint resumed" : "Endpoint paused");
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusyId(null);
    }
  };

  const rotate = async (ep) => {
    if (!window.confirm("Rotate the signing secret? Existing signatures will stop validating.")) return;
    setBusyId(ep.id);
    try {
      const { data } = await api.post(`/webhooks/${ep.id}/rotate`);
      setSecret(data.secret);
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusyId(null);
    }
  };

  const remove = async (ep) => {
    if (!window.confirm(`Delete this webhook endpoint? This cannot be undone.`)) return;
    setBusyId(ep.id);
    try {
      await api.delete(`/webhooks/${ep.id}`);
      toast.success("Webhook deleted");
      load();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusyId(null);
    }
  };

  const hasEndpoints = useMemo(() => endpoints.length > 0, [endpoints]);

  if (loading) {
    return (
      <div className="grid h-[60vh] place-items-center">
        <Loader2 className="h-6 w-6 animate-spin text-[#4F46E5]" />
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-5xl space-y-8 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#EEF2FF] text-[#4F46E5]">
            <WebhookIcon className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#0F172A]">Webhooks</h1>
            <p className="text-sm text-[#64748B]">
              Receive signed, real-time events from OraOne on your own servers.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            data-testid="webhooks-refresh"
            className="inline-flex items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC]"
          >
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
          {canManage && (
            <button
              onClick={() => setShowCreate(true)}
              data-testid="webhooks-create"
              className="inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-3 py-2 text-sm font-semibold text-white hover:bg-[#4338CA]"
            >
              <Plus className="h-4 w-4" /> Add endpoint
            </button>
          )}
        </div>
      </div>

      {!hasEndpoints ? (
        <div className="grid place-items-center rounded-2xl border border-dashed border-[#CBD5E1] bg-white py-16 text-center">
          <WebhookIcon className="mb-3 h-10 w-10 text-[#CBD5E1]" />
          <p className="text-sm font-semibold text-[#0F172A]">No webhook endpoints yet</p>
          <p className="mt-1 max-w-sm text-sm text-[#64748B]">
            Add an endpoint to get notified about conversations, documents, workflows and more.
          </p>
          {canManage && (
            <button
              onClick={() => setShowCreate(true)}
              className="mt-4 inline-flex items-center gap-2 rounded-xl bg-[#4F46E5] px-4 py-2 text-sm font-semibold text-white hover:bg-[#4338CA]"
            >
              <Plus className="h-4 w-4" /> Add your first endpoint
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {endpoints.map((ep) => {
            const busy = busyId === ep.id;
            const open = expanded === ep.id;
            return (
              <div key={ep.id} className="overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white">
                <div className="flex flex-wrap items-start justify-between gap-4 p-5">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <code className="truncate font-mono text-sm font-medium text-[#0F172A]">{ep.url}</code>
                      <StatusBadge status={ep.status} />
                    </div>
                    {ep.description && <p className="mt-1 text-[13px] text-[#64748B]">{ep.description}</p>}
                    <div className="mt-3 flex flex-wrap gap-1">
                      {(ep.events || []).map((e) => (
                        <EventChip key={e}>{e}</EventChip>
                      ))}
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-4 text-[12px] text-[#94A3B8]">
                      <span>Last delivery: {fmtRelative(ep.last_delivery_at)}</span>
                      {ep.last_status && <span>Last status: {ep.last_status}</span>}
                      {ep.failure_count > 0 && <span className="text-[#DC2626]">{ep.failure_count} recent failures</span>}
                    </div>
                  </div>
                  {canManage && (
                    <div className="flex shrink-0 items-center gap-1.5">
                      <button
                        onClick={() => sendTest(ep)}
                        disabled={busy}
                        title="Send test event"
                        data-testid={`webhook-test-${ep.id}`}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-[#E2E8F0] px-2.5 py-1.5 text-[12px] font-medium text-[#475569] hover:bg-[#F8FAFC] disabled:opacity-60"
                      >
                        {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />} Test
                      </button>
                      <button
                        onClick={() => toggleStatus(ep)}
                        disabled={busy}
                        title={ep.status === "active" ? "Pause" : "Resume"}
                        className="rounded-lg border border-[#E2E8F0] p-1.5 text-[#475569] hover:bg-[#F8FAFC] disabled:opacity-60"
                      >
                        {ep.status === "active" ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                      </button>
                      <button
                        onClick={() => rotate(ep)}
                        disabled={busy}
                        title="Rotate signing secret"
                        className="rounded-lg border border-[#E2E8F0] p-1.5 text-[#475569] hover:bg-[#F8FAFC] disabled:opacity-60"
                      >
                        <RotateCcw className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => remove(ep)}
                        disabled={busy}
                        title="Delete endpoint"
                        className="rounded-lg border border-[#FECACA] p-1.5 text-[#DC2626] hover:bg-[#FEF2F2] disabled:opacity-60"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                </div>
                <button
                  onClick={() => setExpanded(open ? null : ep.id)}
                  className="flex w-full items-center justify-between border-t border-[#F1F5F9] bg-[#F8FAFC] px-5 py-2.5 text-[12px] font-medium text-[#475569] hover:bg-[#F1F5F9]"
                >
                  <span>Recent deliveries</span>
                  <ChevronDown className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} />
                </button>
                {open && (
                  <div className="border-t border-[#F1F5F9] p-5">
                    <DeliveriesRow endpointId={ep.id} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {showCreate && (
        <CreateWebhookModal events={events} onClose={() => setShowCreate(false)} onCreated={onCreated} />
      )}
      {secret && <RevealSecretModal secret={secret} onClose={() => setSecret(null)} />}
    </motion.div>
  );
}
