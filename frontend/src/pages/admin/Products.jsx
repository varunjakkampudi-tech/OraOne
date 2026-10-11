import React, { useEffect, useState } from "react";
import { Boxes } from "lucide-react";
import { toast } from "sonner";
import {
  PageHeader, Glass, Badge, Btn, Toggle, LoadingState, ErrorState, EmptyState, useAdminTheme,
} from "@/components/admin/adminKit";
import { useAdminData } from "@/components/admin/useAdminData";
import { superAdminApi } from "@/lib/superAdmin";
import { formatApiError } from "@/lib/api";

const STATUS_TONES = {
  coming_soon: "blue",
  preview: "purple",
  beta: "purple",
  ga: "green",
  active: "green",
  deprecated: "amber",
  maintenance: "amber",
  internal: "slate",
  disabled: "slate",
};
const STATUS_OPTIONS = [
  "coming_soon", "preview", "beta", "ga", "active",
  "deprecated", "maintenance", "internal", "disabled",
];
const VISIBILITY_OPTIONS = ["visible", "hidden", "internal"];

function ProductCard({ product, onSaved }) {
  const { t } = useAdminTheme();
  const [form, setForm] = useState(product);
  const [busy, setBusy] = useState(false);

  useEffect(() => setForm(product), [product]);

  const dirty =
    form.status !== product.status ||
    form.visibility !== product.visibility ||
    form.version !== product.version ||
    (form.release_notes || "") !== (product.release_notes || "") ||
    form.default_enabled !== product.default_enabled;

  const set = (patch) => setForm((f) => ({ ...f, ...patch }));

  async function save() {
    setBusy(true);
    try {
      const updated = await superAdminApi.setProduct(product.key, {
        status: form.status,
        visibility: form.visibility,
        version: form.version,
        release_notes: form.release_notes,
        default_enabled: form.default_enabled,
      });
      toast.success(`${product.name} updated`);
      onSaved(updated.after || updated);
    } catch (e) {
      toast.error(formatApiError(e?.response?.data?.detail) || "Failed to update product.");
    } finally {
      setBusy(false);
    }
  }

  const labelCls = "block text-[11px] font-medium mb-1";
  const inputCls =
    "w-full rounded-lg border border-[#E2E8F0] bg-white px-3 py-2 text-sm outline-none focus:border-[#2563EB]";

  return (
    <Glass className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold" style={{ color: t.ink }}>{product.name}</span>
            <Badge tone={STATUS_TONES[form.status] || "slate"}>{form.status}</Badge>
            {form.visibility === "hidden" && <Badge tone="slate">hidden</Badge>}
          </div>
          <p className="mt-0.5 text-xs" style={{ color: t.sub }}>{product.description}</p>
          <p className="mt-1 font-mono text-[11px]" style={{ color: t.muted }}>{product.key}</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label className={labelCls} style={{ color: t.sub }}>Status</label>
          <select className={inputCls} value={form.status} onChange={(e) => set({ status: e.target.value })}>
            {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className={labelCls} style={{ color: t.sub }}>Visibility</label>
          <select className={inputCls} value={form.visibility} onChange={(e) => set({ visibility: e.target.value })}>
            {VISIBILITY_OPTIONS.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </div>
        <div>
          <label className={labelCls} style={{ color: t.sub }}>Version</label>
          <input className={inputCls} value={form.version || ""} onChange={(e) => set({ version: e.target.value })} placeholder="1.0.0" />
        </div>
      </div>

      <div className="mt-3">
        <label className={labelCls} style={{ color: t.sub }}>Release notes</label>
        <textarea
          className={`${inputCls} min-h-[80px] resize-y`}
          value={form.release_notes || ""}
          onChange={(e) => set({ release_notes: e.target.value })}
          placeholder="What changed in this release…"
        />
      </div>

      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Toggle checked={!!form.default_enabled} onChange={() => set({ default_enabled: !form.default_enabled })} disabled={busy} />
          <div>
            <div className="text-sm font-medium" style={{ color: t.ink }}>Default enabled</div>
            <div className="text-[11px]" style={{ color: t.muted }}>New workspaces get this product unless overridden.</div>
          </div>
        </div>
        <Btn onClick={save} disabled={!dirty || busy} variant={dirty ? "primary" : "ghost"}>
          {busy ? "Saving…" : "Save changes"}
        </Btn>
      </div>
    </Glass>
  );
}

function AdoptionStrip() {
  const { t } = useAdminTheme();
  const { data } = useAdminData(() => superAdminApi.entitlementsOverview(), []);
  const items = data?.products || [];
  if (!items.length) return null;
  return (
    <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((p) => {
        const total = p.total_orgs || 0;
        const pct = total ? Math.round((p.enabled_orgs / total) * 100) : 0;
        return (
          <Glass key={p.key} className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold" style={{ color: t.ink }}>{p.name}</span>
              <Badge tone={STATUS_TONES[p.status] || "slate"}>{p.status}</Badge>
            </div>
            <div className="mt-2 flex items-end gap-1">
              <span className="text-2xl font-bold" style={{ color: t.ink }}>{p.enabled_orgs}</span>
              <span className="text-xs mb-1" style={{ color: t.muted }}>/ {total} orgs enabled</span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#EEF2F7]">
              <div className="h-full rounded-full bg-[#2563EB]" style={{ width: `${pct}%` }} />
            </div>
            <div className="mt-2 text-[11px]" style={{ color: t.muted }}>
              {p.overrides} override{p.overrides === 1 ? "" : "s"} · {p.disabled_orgs} disabled
            </div>
          </Glass>
        );
      })}
    </div>
  );
}

export default function AdminProducts() {
  const { data, loading, error, reload, setData } = useAdminData(() => superAdminApi.products(), []);

  const handleSaved = (updated) =>
    setData((prev) => (prev || []).map((p) => (p.key === updated.key ? { ...p, ...updated } : p)));

  return (
    <div>
      <PageHeader
        icon={Boxes}
        title="Products"
        subtitle="Manage OraOne's licensable products — launch status, visibility, version & release notes."
      />
      <AdoptionStrip />
      {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={reload} /> : (data || []).length === 0 ? (
        <EmptyState icon={Boxes} title="No products" />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {data.map((product) => (
            <ProductCard key={product.key} product={product} onSaved={handleSaved} />
          ))}
        </div>
      )}
    </div>
  );
}
