import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Palette,
  Loader2,
  RefreshCw,
  Save,
  Lock,
  Sparkles,
  Globe,
  EyeOff,
  ExternalLink,
  Upload,
  Trash2,
  Image as ImageIcon,
} from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";
import { usePermissions } from "@/hooks/usePermissions";
import { useBranding } from "@/hooks/useBranding";

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/;
const EMPTY = {
  brand_name: "",
  logo_url: "",
  icon_url: "",
  primary_color: "#4F46E5",
  accent_color: "#06B6D4",
  support_email: "",
  support_url: "",
  custom_domain: "",
  hide_powered_by: false,
};

function Field({ label, hint, children }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-[#334155]">{label}</label>
      {children}
      {hint && <p className="text-xs text-[#94A3B8]">{hint}</p>}
    </div>
  );
}

function PremiumLock() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-[#FEF3C7] px-2 py-0.5 text-[11px] font-semibold text-[#B45309]">
      <Lock size={11} /> Business
    </span>
  );
}

// Drag-and-drop / click image uploader with an instant preview.
function LogoUploader({ value, uploading, disabled, wide, onPick, onClear, testid }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const pick = (file) => {
    if (file && !disabled) onPick(file);
  };

  return (
    <div>
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        data-testid={testid}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          pick(e.dataTransfer.files?.[0]);
        }}
        className={`relative flex ${wide ? "h-24" : "h-24"} cursor-pointer items-center justify-center gap-3 overflow-hidden rounded-xl border-2 border-dashed px-4 text-center transition-colors ${
          dragOver ? "border-[#2563EB] bg-[#EFF6FF]" : "border-[#E2E8F0] bg-[#F8FAFC] hover:border-[#CBD5E1]"
        } ${disabled ? "cursor-not-allowed opacity-60" : ""}`}
      >
        {value ? (
          <img
            src={value}
            alt="Brand asset preview"
            className={`${wide ? "max-h-16" : "max-h-16 max-w-16"} object-contain`}
          />
        ) : (
          <div className="flex flex-col items-center gap-1 text-[#64748B]">
            <ImageIcon size={20} className="text-[#94A3B8]" />
            <span className="text-xs font-medium">
              Drag &amp; drop or <span className="text-[#2563EB]">browse</span>
            </span>
          </div>
        )}
        {uploading && (
          <div className="absolute inset-0 grid place-items-center bg-white/70">
            <Loader2 size={20} className="animate-spin text-[#2563EB]" />
          </div>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/svg+xml,image/webp,image/gif"
        className="hidden"
        disabled={disabled}
        onChange={(e) => {
          pick(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {value && !disabled && (
        <div className="mt-1.5 flex items-center gap-3 text-xs">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="inline-flex items-center gap-1 font-medium text-[#2563EB] hover:underline"
          >
            <Upload size={12} /> Replace
          </button>
          <button
            type="button"
            onClick={onClear}
            className="inline-flex items-center gap-1 font-medium text-[#EF4444] hover:underline"
          >
            <Trash2 size={12} /> Remove
          </button>
        </div>
      )}
    </div>
  );
}

export default function Branding() {
  const { can } = usePermissions();
  const { branding: ctxBranding, refresh: refreshCtx } = useBranding();
  const [server, setServer] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState({ logo: false, icon: false });

  const canManage = can("settings.manage");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/branding");
      setServer(data);
      setForm({
        brand_name: data.brand_name || "",
        logo_url: data.logo_url || "",
        icon_url: data.icon_url || "",
        primary_color: data.primary_color || "#4F46E5",
        accent_color: data.accent_color || "#06B6D4",
        support_email: data.support_email || "",
        support_url: data.support_url || "",
        custom_domain: data.custom_domain || "",
        hide_powered_by: !!data.hide_powered_by,
      });
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const whiteLabel = !!server?.white_label_enabled;
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  const dirty = useMemo(() => {
    if (!server) return false;
    return (
      (server.brand_name || "") !== form.brand_name ||
      (server.logo_url || "") !== form.logo_url ||
      (server.icon_url || "") !== form.icon_url ||
      (server.primary_color || "") !== form.primary_color ||
      (server.accent_color || "") !== form.accent_color ||
      (server.support_email || "") !== form.support_email ||
      (server.support_url || "") !== form.support_url ||
      (server.custom_domain || "") !== form.custom_domain ||
      !!server.hide_powered_by !== form.hide_powered_by
    );
  }, [server, form]);

  const primaryValid = HEX_RE.test(form.primary_color);
  const accentValid = HEX_RE.test(form.accent_color);

  const save = async () => {
    if (!primaryValid || !accentValid) {
      toast.error("Colours must be hex values like #4F46E5.");
      return;
    }
    setSaving(true);
    try {
      const { data } = await api.put("/branding", form);
      setServer(data);
      toast.success("Branding saved");
      refreshCtx();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSaving(false);
    }
  };

  const previewName = form.brand_name || server?.organization_name || "Your Brand";

  // Upload a logo/icon image. The backend stores it and returns the hosted URL,
  // which we fold straight into the form/server state for an instant preview.
  const uploadAsset = async (field, file) => {
    if (!file) return;
    if (!/^image\//.test(file.type)) {
      toast.error("Choose an image file (PNG, JPG, SVG, WEBP).");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      toast.error("Image must be 2 MB or smaller.");
      return;
    }
    setUploading((u) => ({ ...u, [field]: true }));
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post(`/branding/${field}`, fd, {
        headers: { "Content-Type": undefined },
      });
      const url = field === "logo" ? data.logo_url : data.icon_url;
      setServer(data);
      setForm((f) => ({ ...f, [`${field}_url`]: url || "" }));
      toast.success(`${field === "logo" ? "Logo" : "Icon"} uploaded`);
      refreshCtx();
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setUploading((u) => ({ ...u, [field]: false }));
    }
  };

  const clearAsset = (field) => set(`${field}_url`)("");

  if (loading) {
    return (
      <div className="grid h-64 place-items-center text-[#64748B]">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-[#0F172A]">
            <Palette size={24} /> Branding
          </h1>
          <p className="mt-1 text-sm text-[#64748B]">
            White-label your workspace with your own brand identity.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            data-testid="branding-refresh"
            className="inline-flex items-center gap-2 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC]"
          >
            <RefreshCw size={16} /> Refresh
          </button>
          {canManage && (
            <button
              onClick={save}
              disabled={!dirty || saving}
              data-testid="branding-save"
              className="inline-flex items-center gap-2 rounded-full bg-[#2563EB] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#1D4ED8] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
              Save changes
            </button>
          )}
        </div>
      </div>

      {!whiteLabel && (
        <div className="flex items-center justify-between gap-4 rounded-2xl border border-[#FDE68A] bg-[#FFFBEB] px-4 py-3">
          <div className="flex items-center gap-3 text-sm text-[#92400E]">
            <Sparkles size={18} />
            <span>
              You're on the <b className="capitalize">{server?.plan_code}</b> plan. Custom domains
              and hiding the “Powered by” mark require Business or higher.
            </span>
          </div>
          <Link
            to="/app/billing"
            className="shrink-0 rounded-lg bg-[#92400E] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#78350F]"
          >
            Upgrade
          </Link>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        {/* Form */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6 rounded-2xl border border-[#E2E8F0] bg-white p-6"
        >
          <fieldset disabled={!canManage} className="space-y-6 disabled:opacity-70">
            <Field label="Brand name" hint="Shown in the sidebar and customer-facing surfaces.">
              <input
                type="text"
                value={form.brand_name}
                onChange={(e) => set("brand_name")(e.target.value)}
                placeholder={server?.organization_name || "Acme Inc."}
                maxLength={120}
                data-testid="branding-brand-name"
                className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20"
              />
            </Field>

            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Logo" hint="Wide logo for the sidebar header. PNG, SVG or WEBP, up to 2 MB.">
                <LogoUploader
                  value={form.logo_url}
                  uploading={uploading.logo}
                  disabled={!canManage}
                  wide
                  onPick={(file) => uploadAsset("logo", file)}
                  onClear={() => clearAsset("logo")}
                  testid="branding-logo-upload"
                />
              </Field>
              <Field label="Icon" hint="Square mark / favicon. PNG or SVG, up to 2 MB.">
                <LogoUploader
                  value={form.icon_url}
                  uploading={uploading.icon}
                  disabled={!canManage}
                  onPick={(file) => uploadAsset("icon", file)}
                  onClear={() => clearAsset("icon")}
                  testid="branding-icon-upload"
                />
              </Field>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Primary colour">
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={primaryValid ? form.primary_color.slice(0, 7) : "#4F46E5"}
                    onChange={(e) => set("primary_color")(e.target.value)}
                    className="h-10 w-12 cursor-pointer rounded-lg border border-[#E2E8F0] bg-white p-1"
                  />
                  <input
                    type="text"
                    value={form.primary_color}
                    onChange={(e) => set("primary_color")(e.target.value)}
                    data-testid="branding-primary-color"
                    className={`w-full rounded-xl border px-3 py-2 text-sm uppercase outline-none focus:ring-2 ${
                      primaryValid
                        ? "border-[#E2E8F0] focus:border-[#2563EB] focus:ring-[#2563EB]/20"
                        : "border-[#FCA5A5] focus:ring-[#EF4444]/20"
                    }`}
                  />
                </div>
              </Field>
              <Field label="Accent colour">
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={accentValid ? form.accent_color.slice(0, 7) : "#06B6D4"}
                    onChange={(e) => set("accent_color")(e.target.value)}
                    className="h-10 w-12 cursor-pointer rounded-lg border border-[#E2E8F0] bg-white p-1"
                  />
                  <input
                    type="text"
                    value={form.accent_color}
                    onChange={(e) => set("accent_color")(e.target.value)}
                    data-testid="branding-accent-color"
                    className={`w-full rounded-xl border px-3 py-2 text-sm uppercase outline-none focus:ring-2 ${
                      accentValid
                        ? "border-[#E2E8F0] focus:border-[#2563EB] focus:ring-[#2563EB]/20"
                        : "border-[#FCA5A5] focus:ring-[#EF4444]/20"
                    }`}
                  />
                </div>
              </Field>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Support email">
                <input
                  type="email"
                  value={form.support_email}
                  onChange={(e) => set("support_email")(e.target.value)}
                  placeholder="support@acme.com"
                  data-testid="branding-support-email"
                  className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20"
                />
              </Field>
              <Field label="Support URL">
                <input
                  type="url"
                  value={form.support_url}
                  onChange={(e) => set("support_url")(e.target.value)}
                  placeholder="https://acme.com/help"
                  data-testid="branding-support-url"
                  className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20"
                />
              </Field>
            </div>

            {/* Premium */}
            <div className="space-y-5 rounded-xl border border-dashed border-[#E2E8F0] bg-[#F8FAFC] p-4">
              <Field
                label={
                  <span className="flex items-center gap-2">
                    <Globe size={14} /> Custom domain {!whiteLabel && <PremiumLock />}
                  </span>
                }
                hint="Point a CNAME at your workspace, e.g. app.acme.com."
              >
                <input
                  type="text"
                  value={form.custom_domain}
                  onChange={(e) => set("custom_domain")(e.target.value)}
                  disabled={!whiteLabel}
                  placeholder="app.acme.com"
                  data-testid="branding-custom-domain"
                  className="w-full rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/20 disabled:cursor-not-allowed disabled:bg-[#F1F5F9]"
                />
              </Field>
              <label
                className={`flex items-center gap-3 ${
                  whiteLabel ? "cursor-pointer" : "cursor-not-allowed opacity-70"
                }`}
              >
                <input
                  type="checkbox"
                  checked={form.hide_powered_by}
                  disabled={!whiteLabel}
                  onChange={(e) => set("hide_powered_by")(e.target.checked)}
                  data-testid="branding-hide-powered"
                  className="size-4 rounded border-[#CBD5E1] text-[#2563EB] focus:ring-[#2563EB]"
                />
                <span className="flex items-center gap-2 text-sm font-medium text-[#334155]">
                  <EyeOff size={14} /> Hide “Powered by Ora One”
                  {!whiteLabel && <PremiumLock />}
                </span>
              </label>
            </div>
          </fieldset>

          {!canManage && (
            <p className="rounded-lg bg-[#F1F5F9] px-3 py-2 text-xs text-[#64748B]">
              You have read-only access to branding. Ask an admin to make changes.
            </p>
          )}
        </motion.div>

        {/* Live preview */}
        <div className="space-y-4">
          <div className="overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white">
            <div
              className="h-20 w-full"
              style={{
                background: `linear-gradient(135deg, ${
                  primaryValid ? form.primary_color : "#4F46E5"
                }, ${accentValid ? form.accent_color : "#06B6D4"})`,
              }}
            />
            <div className="-mt-8 px-5 pb-5">
              <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-2xl border-4 border-white bg-white shadow-sm">
                {form.icon_url || form.logo_url ? (
                  <img
                    src={form.icon_url || form.logo_url}
                    alt="Brand"
                    className="h-full w-full object-contain"
                  />
                ) : (
                  <span
                    className="grid h-full w-full place-items-center text-xl font-bold text-white"
                    style={{ backgroundColor: primaryValid ? form.primary_color : "#4F46E5" }}
                  >
                    {previewName.slice(0, 1).toUpperCase()}
                  </span>
                )}
              </div>
              <p className="mt-3 text-base font-bold text-[#0F172A]">{previewName}</p>
              <p className="text-xs text-[#64748B]">Live preview</p>
              <div className="mt-4 space-y-2">
                <button
                  className="w-full rounded-xl py-2 text-sm font-semibold text-white"
                  style={{ backgroundColor: primaryValid ? form.primary_color : "#4F46E5" }}
                >
                  Primary action
                </button>
                <button
                  className="w-full rounded-xl py-2 text-sm font-semibold text-white"
                  style={{ backgroundColor: accentValid ? form.accent_color : "#06B6D4" }}
                >
                  Accent action
                </button>
              </div>
              {!form.hide_powered_by && (
                <p className="mt-4 text-center text-[11px] text-[#94A3B8]">
                  Powered by Ora One
                </p>
              )}
            </div>
          </div>

          {server?.custom_domain && (
            <a
              href={`https://${server.custom_domain}`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center justify-between gap-2 rounded-xl border border-[#E2E8F0] bg-white px-4 py-3 text-sm text-[#334155] hover:bg-[#F8FAFC]"
            >
              <span className="flex items-center gap-2">
                <Globe size={15} /> {server.custom_domain}
              </span>
              <ExternalLink size={14} className="text-[#94A3B8]" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
