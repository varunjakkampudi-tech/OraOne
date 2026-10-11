import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import {
  Rocket,
  Copy,
  Check,
  Loader2,
  Globe,
  Phone,
  Code2,
  Webhook,
  FormInput,
  MessagesSquare,
  MessageSquare,
  Plus,
  X,
  ShieldCheck,
  PlayCircle,
  Package,
  Terminal,
  Palette,
  Sparkles,
  CheckCircle2,
  CircleDot,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";

// ───────────────────────── helpers ─────────────────────────

const CHANNEL_ICONS = {
  messages: MessagesSquare,
  bubble: MessageSquare,
  phone: Phone,
  code: Code2,
  webhook: Webhook,
  form: FormInput,
};

const DEPLOY_STATUS = {
  live: { label: "Live", cls: "bg-green-50 text-green-700 border-green-200", dot: "#16A34A" },
  draft: { label: "Draft", cls: "bg-slate-50 text-slate-600 border-slate-200", dot: "#94A3B8" },
  paused: { label: "Paused", cls: "bg-amber-50 text-amber-700 border-amber-200", dot: "#D97706" },
};

function CopyButton({ text, label = "Copy", className = "" }) {
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      toast.success("Copied to clipboard");
      setTimeout(() => setDone(false), 1500);
    } catch {
      toast.error("Could not copy");
    }
  };
  return (
    <button
      onClick={copy}
      type="button"
      className={`inline-flex items-center gap-1.5 text-xs font-semibold rounded-lg px-2.5 py-1.5 transition ${className || "bg-white/10 text-white hover:bg-white/20"}`}
    >
      {done ? <Check size={13} /> : <Copy size={13} />}
      {done ? "Copied" : label}
    </button>
  );
}

function CodeBlock({ code, language = "" }) {
  return (
    <div className="relative rounded-xl bg-[#0B1220] border border-[#1E293B] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#1E293B]">
        <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">{language || "code"}</span>
        <CopyButton text={code} />
      </div>
      <pre className="p-4 overflow-x-auto text-[12.5px] leading-relaxed text-slate-100 font-mono whitespace-pre">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${checked ? "bg-[#2563EB]" : "bg-slate-300"} ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition ${checked ? "translate-x-6" : "translate-x-1"}`} />
    </button>
  );
}

function SectionCard({ title, subtitle, icon: Icon, right, children }) {
  return (
    <section className="rounded-2xl border border-[#E2E8F0] bg-white">
      <header className="flex items-start justify-between gap-4 px-5 py-4 border-b border-[#F1F5F9]">
        <div className="flex items-start gap-3">
          {Icon ? (
            <div className="mt-0.5 h-9 w-9 rounded-xl bg-[#EFF4FF] text-[#2563EB] grid place-items-center shrink-0">
              <Icon size={18} />
            </div>
          ) : null}
          <div>
            <h2 className="text-[15px] font-semibold text-[#0F172A]">{title}</h2>
            {subtitle ? <p className="text-[13px] text-[#64748B] mt-0.5">{subtitle}</p> : null}
          </div>
        </div>
        {right}
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
}

// ───────────────────────── page ─────────────────────────

export default function Deploy() {
  const { id: routeAgentId } = useParams();
  const [searchParams] = useSearchParams();

  const [agents, setAgents] = useState([]);
  const [agentId, setAgentId] = useState(routeAgentId || searchParams.get("agent") || "");
  const [channels, setChannels] = useState([]);
  const [deploy, setDeploy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyChannel, setBusyChannel] = useState(null);
  const [publishing, setPublishing] = useState(false);
  const [verifying, setVerifying] = useState(false);

  const [installTab, setInstallTab] = useState("embed"); // embed | npm | sdk
  const [platform, setPlatform] = useState("html");

  const [domains, setDomains] = useState([]);
  const [domainInput, setDomainInput] = useState("");
  const [savingDomains, setSavingDomains] = useState(false);

  const [previewOn, setPreviewOn] = useState(false);

  // Load the agent roster once.
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/agents", { params: { limit: 100 } });
        const items = data.items || [];
        setAgents(items);
        setAgentId((cur) => cur || routeAgentId || (items[0] && items[0].id) || "");
      } catch (e) {
        toast.error(formatApiError(e));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const load = useCallback(async (aid) => {
    if (!aid) return;
    setLoading(true);
    try {
      const [{ data: ch }, { data: dep }] = await Promise.all([
        api.get(`/agents/${aid}/channels`),
        api.get(`/agents/${aid}/deploy`),
      ]);
      setChannels(ch.items || []);
      setDeploy(dep);
      setDomains(dep.domains || []);
    } catch (e) {
      toast.error(formatApiError(e));
      setDeploy(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (agentId) load(agentId);
  }, [agentId, load]);

  const toggleChannel = async (channel, enabled) => {
    setBusyChannel(channel);
    try {
      const { data } = await api.patch(`/agents/${agentId}/channels/${channel}`, { enabled });
      setChannels((rows) => rows.map((r) => (r.channel === channel ? data : r)));
      // Embeddable toggles can change deploy status — refresh it.
      if (channel === "widget" || channel === "chat") load(agentId);
      toast.success(`${data.label} ${enabled ? "enabled" : "disabled"}`);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusyChannel(null);
    }
  };

  const publish = async (next) => {
    setPublishing(true);
    try {
      const { data } = await api.post(`/agents/${agentId}/deploy/publish`, { publish: next });
      setDeploy(data);
      setDomains(data.domains || []);
      load(agentId);
      toast.success(next ? "Agent is live" : "Deployment paused");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setPublishing(false);
    }
  };

  const verify = async () => {
    setVerifying(true);
    try {
      const { data } = await api.post(`/agents/${agentId}/deploy/verify`);
      setDeploy((d) => (d ? { ...d, verification: data } : d));
      if (data.installed) toast.success("Widget detected on a live page");
      else toast.message("No installs detected yet", { description: "Add the snippet to your site, then re-check." });
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setVerifying(false);
    }
  };

  const addDomain = () => {
    const v = domainInput.trim().toLowerCase();
    if (!v) return;
    if (domains.includes(v)) {
      setDomainInput("");
      return;
    }
    setDomains((d) => [...d, v]);
    setDomainInput("");
  };

  const saveDomains = async () => {
    setSavingDomains(true);
    try {
      const { data } = await api.put(`/agents/${agentId}/deploy/domains`, { domains });
      setDomains(data.domains || []);
      toast.success("Allowed domains updated");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setSavingDomains(false);
    }
  };

  // Live test: inject the REAL widget loader onto this dashboard page.
  // The public widget API only serves published widgets, so a widget still
  // in "draft" must be auto-published first — otherwise this silently 403s
  // and the user has no idea their agent isn't actually testable yet.
  const launchPreview = async () => {
    if (!deploy) return;
    if (previewOn) {
      // Tear down.
      try {
        document.querySelectorAll("[data-oraone-preview]").forEach((n) => n.remove());
        if (window.OraOneWidget && window.OraOneWidget.close) window.OraOneWidget.close();
      } catch {
        /* noop */
      }
      setPreviewOn(false);
      return;
    }
    let activeDeploy = deploy;
    if (deploy.deploy_status !== "live") {
      setPublishing(true);
      try {
        const { data } = await api.post(`/agents/${agentId}/deploy/publish`, { publish: true });
        setDeploy(data);
        setDomains(data.domains || []);
        activeDeploy = data;
        toast.success("Published so you can test it live");
      } catch (e) {
        toast.error(formatApiError(e) || "Could not publish this widget for testing");
        setPublishing(false);
        return;
      }
      setPublishing(false);
    }
    const s = document.createElement("script");
    s.src = `${activeDeploy.cdn_base}/widget.js`;
    s.setAttribute("data-widget-id", activeDeploy.public_key);
    if (activeDeploy.api_base && activeDeploy.api_base !== activeDeploy.cdn_base) s.setAttribute("data-api", activeDeploy.api_base);
    s.setAttribute("data-oraone-preview", "1");
    s.async = true;
    document.body.appendChild(s);
    setPreviewOn(true);
    toast.success("Test widget loaded — look bottom-right");
  };

  useEffect(() => {
    return () => {
      try {
        document.querySelectorAll("[data-oraone-preview]").forEach((n) => n.remove());
      } catch {
        /* noop */
      }
    };
  }, []);

  const guide = useMemo(
    () => (deploy?.install_guides || []).find((g) => g.platform === platform) || deploy?.install_guides?.[0],
    [deploy, platform]
  );

  const statusMeta = DEPLOY_STATUS[deploy?.deploy_status] || DEPLOY_STATUS.draft;

  return (
    <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-6 space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="h-11 w-11 rounded-2xl bg-[#0F172A] text-white grid place-items-center">
            <Rocket size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#0F172A]">Channels &amp; Deploy</h1>
            <p className="text-[13px] text-[#64748B]">One agent, every channel. Ship it to your site in minutes.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {agents.length > 0 && (
            <select
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm font-medium text-[#0F172A] focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
            >
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {loading || !deploy ? (
        <div className="grid place-items-center py-24 text-[#64748B]">
          <Loader2 className="animate-spin" size={26} />
        </div>
      ) : (
        <>
          {/* Deploy status bar */}
          <div className="rounded-2xl border border-[#E2E8F0] bg-white px-5 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${statusMeta.cls}`}>
                <CircleDot size={12} style={{ color: statusMeta.dot }} />
                {statusMeta.label}
              </span>
              <div className="text-sm text-[#334155]">
                <span className="font-semibold text-[#0F172A]">{deploy.agent_name}</span>
                <span className="text-[#94A3B8]"> · key </span>
                <code className="text-[12px] bg-[#F1F5F9] rounded px-1.5 py-0.5 font-mono text-[#475569]">{deploy.public_key}</code>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={verify}
                disabled={verifying}
                className="inline-flex items-center gap-1.5 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm font-semibold text-[#334155] hover:bg-[#F8FAFC] disabled:opacity-60"
              >
                {verifying ? <Loader2 size={15} className="animate-spin" /> : <ShieldCheck size={15} />}
                Verify install
              </button>
              {deploy.deploy_status === "live" ? (
                <button
                  onClick={() => publish(false)}
                  disabled={publishing}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700 hover:bg-amber-100 disabled:opacity-60"
                >
                  {publishing ? <Loader2 size={15} className="animate-spin" /> : null}
                  Pause
                </button>
              ) : (
                <button
                  onClick={() => publish(true)}
                  disabled={publishing}
                  className="inline-flex items-center gap-1.5 rounded-full bg-[#2563EB] px-3.5 py-2 text-sm font-semibold text-white hover:bg-[#1D4ED8] disabled:opacity-60"
                >
                  {publishing ? <Loader2 size={15} className="animate-spin" /> : <Rocket size={15} />}
                  Publish &amp; go live
                </button>
              )}
            </div>
          </div>

          {/* Verification result */}
          {deploy.verification ? (
            <div
              className={`rounded-xl border px-4 py-3 text-sm flex items-center gap-2 ${
                deploy.verification.installed
                  ? "border-green-200 bg-green-50 text-green-800"
                  : "border-slate-200 bg-slate-50 text-slate-600"
              }`}
            >
              {deploy.verification.installed ? <CheckCircle2 size={16} /> : <CircleDot size={16} />}
              {deploy.verification.installed
                ? `Installed — ${deploy.verification.loads_count} load(s) detected${
                    deploy.verification.last_seen ? ` · last seen ${new Date(deploy.verification.last_seen).toLocaleString()}` : ""
                  }`
                : "Not detected yet. Add a snippet below to your site, publish, then click “Verify install”."}
            </div>
          ) : null}

          {/* Channels */}
          <SectionCard
            title="Channels"
            subtitle="Turn on the ways customers reach this agent. The same brain answers everywhere."
            icon={Sparkles}
          >
            <div className="grid sm:grid-cols-2 gap-3">
              {channels.map((c) => {
                const Icon = CHANNEL_ICONS[c.icon] || Code2;
                return (
                  <div
                    key={c.channel}
                    className={`rounded-xl border p-4 flex items-start justify-between gap-3 transition ${
                      c.enabled ? "border-[#BFD3FF] bg-[#F7FAFF]" : "border-[#E2E8F0] bg-white"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`h-9 w-9 rounded-lg grid place-items-center shrink-0 ${c.enabled ? "bg-[#2563EB] text-white" : "bg-[#F1F5F9] text-[#64748B]"}`}>
                        <Icon size={17} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-[#0F172A]">{c.label}</span>
                          {c.embeddable ? (
                            <span className="text-[10px] font-semibold uppercase tracking-wide text-[#2563EB] bg-[#EFF4FF] rounded px-1.5 py-0.5">Embed</span>
                          ) : null}
                        </div>
                        <p className="text-[12.5px] text-[#64748B] mt-0.5">{c.description}</p>
                      </div>
                    </div>
                    <div className="pt-1">
                      {busyChannel === c.channel ? (
                        <Loader2 size={16} className="animate-spin text-[#94A3B8]" />
                      ) : (
                        <Toggle checked={c.enabled} onChange={(v) => toggleChannel(c.channel, v)} />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </SectionCard>

          {/* Install / Deploy */}
          <SectionCard
            title="Install on your website"
            subtitle="Three ways to add OraOne to any modern web app — pick what fits your stack."
            icon={Code2}
            right={
              <div className="flex items-center gap-2">
                {deploy.deploy_status === "live" && (
                  <span data-tour="deploy-live-badge" className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2.5 py-1 text-[11px] font-semibold text-green-700 border border-green-200">
                    <CheckCircle2 size={12} /> Live
                  </span>
                )}
                <button
                  onClick={launchPreview}
                  disabled={publishing}
                  data-tour="deploy-test-widget-btn"
                  className="inline-flex items-center gap-1.5 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm font-semibold text-[#334155] hover:bg-[#F8FAFC] disabled:opacity-60"
                >
                  {publishing ? <Loader2 size={15} className="animate-spin" /> : <PlayCircle size={15} />}
                  {previewOn ? "Stop test" : "Test widget"}
                </button>
              </div>
            }
          >
            {/* Method tabs */}
            <div className="inline-flex rounded-xl bg-[#F1F5F9] p-1 mb-4">
              {[
                { key: "embed", label: "One-line embed", icon: Code2 },
                { key: "npm", label: "NPM package", icon: Package },
                { key: "sdk", label: "JavaScript SDK", icon: Terminal },
              ].map((t) => (
                <button
                  key={t.key}
                  onClick={() => setInstallTab(t.key)}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-[13px] font-semibold transition ${
                    installTab === t.key ? "bg-white text-[#0F172A] shadow-sm" : "text-[#64748B] hover:text-[#334155]"
                  }`}
                >
                  <t.icon size={14} />
                  {t.label}
                </button>
              ))}
            </div>

            {installTab === "embed" && (
              <div className="space-y-3">
                <p className="text-[13px] text-[#64748B]">
                  Paste this once before <code className="bg-[#F1F5F9] rounded px-1 py-0.5 font-mono text-[12px]">&lt;/body&gt;</code>. No build step required.
                </p>
                <CodeBlock code={deploy.snippets.one_line} language="html" />
              </div>
            )}

            {installTab === "npm" && (
              <div className="space-y-3">
                <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-[12.5px] text-amber-800">
                  <ShieldCheck size={15} className="mt-0.5 shrink-0" />
                  <span>
                    The <code className="rounded bg-white/70 px-1 py-0.5 font-mono text-[11.5px]">@oraone/widget</code> npm
                    package isn't published yet — use the <strong>One-line embed</strong> or <strong>JavaScript SDK</strong>{" "}
                    tab instead for now, they work today.
                  </span>
                </div>
                <p className="text-[13px] text-[#64748B]">Once published, install the package and initialise the SDK like this.</p>
                <CodeBlock code={deploy.snippets.npm_install} language="bash" />
                <CodeBlock code={deploy.snippets.npm_import} language="javascript" />
              </div>
            )}

            {installTab === "sdk" && (
              <div className="space-y-3">
                <p className="text-[13px] text-[#64748B]">Load the script and drive everything programmatically.</p>
                <CodeBlock code={deploy.snippets.sdk} language="html" />
              </div>
            )}

            {/* Per-platform guides */}
            <div className="mt-6">
              <h3 className="text-[13px] font-semibold text-[#0F172A] mb-2">Framework guides</h3>
              <div className="flex flex-wrap gap-1.5 mb-3">
                {(deploy.install_guides || []).map((g) => (
                  <button
                    key={g.platform}
                    onClick={() => setPlatform(g.platform)}
                    className={`rounded-lg px-3 py-1.5 text-[12.5px] font-semibold border transition ${
                      platform === g.platform
                        ? "border-[#2563EB] bg-[#EFF4FF] text-[#2563EB]"
                        : "border-[#E2E8F0] bg-white text-[#64748B] hover:bg-[#F8FAFC]"
                    }`}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
              {guide ? <CodeBlock code={guide.code} language={guide.language} /> : null}
            </div>
          </SectionCard>

          {/* Triggers */}
          <SectionCard
            title="Button &amp; form triggers"
            subtitle="Open chat, request a call, or capture a lead from your own UI."
            icon={Sparkles}
          >
            <div className="space-y-4">
              {(deploy.trigger_snippets || []).map((t) => (
                <div key={t.name}>
                  <div className="text-[13px] font-semibold text-[#0F172A] mb-1.5">{t.name}</div>
                  <CodeBlock code={t.code} language={t.language} />
                </div>
              ))}
            </div>
          </SectionCard>

          {/* SDK reference */}
          <SectionCard title="SDK reference" subtitle="The full window.OraOne surface." icon={Terminal}>
            <div className="divide-y divide-[#F1F5F9]">
              {(deploy.sdk_methods || []).map((m) => (
                <div key={m.name} className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4 py-2.5">
                  <code className="text-[12.5px] font-mono text-[#2563EB] sm:w-[280px] shrink-0">{m.name}</code>
                  <span className="text-[13px] text-[#475569]">{m.description}</span>
                </div>
              ))}
            </div>
          </SectionCard>

          {/* Domain whitelist */}
          <SectionCard
            title="Allowed domains"
            subtitle="The widget only loads & answers on these hosts. Leave empty to allow everywhere (dev only)."
            icon={Globe}
            right={
              <button
                onClick={saveDomains}
                disabled={savingDomains}
                className="inline-flex items-center gap-1.5 rounded-xl bg-[#0F172A] px-3 py-2 text-sm font-semibold text-white hover:bg-[#1E293B] disabled:opacity-60"
              >
                {savingDomains ? <Loader2 size={15} className="animate-spin" /> : null}
                Save
              </button>
            }
          >
            <div className="flex items-center gap-2 mb-3">
              <input
                value={domainInput}
                onChange={(e) => setDomainInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addDomain();
                  }
                }}
                placeholder="example.com"
                className="flex-1 rounded-xl border border-[#E2E8F0] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/30"
              />
              <button
                onClick={addDomain}
                className="inline-flex items-center gap-1.5 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm font-semibold text-[#334155] hover:bg-[#F8FAFC]"
              >
                <Plus size={15} /> Add
              </button>
            </div>
            {domains.length === 0 ? (
              <p className="text-[13px] text-[#94A3B8]">No domains pinned — widget is unrestricted. Add your production host before going live.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {domains.map((d) => (
                  <span key={d} className="inline-flex items-center gap-1.5 rounded-lg bg-[#F1F5F9] px-2.5 py-1.5 text-[13px] font-medium text-[#334155]">
                    <Globe size={13} className="text-[#94A3B8]" />
                    {d}
                    <button onClick={() => setDomains((arr) => arr.filter((x) => x !== d))} className="text-[#94A3B8] hover:text-[#EF4444]">
                      <X size={13} />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </SectionCard>

          {/* Footer hint */}
          <div className="rounded-2xl border border-dashed border-[#CBD5E1] bg-[#F8FAFC] px-5 py-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-[13px] text-[#475569]">
              <Palette size={16} className="text-[#94A3B8]" />
              Want to fully theme the bubble, colours and launcher? Use the widget designer.
            </div>
            <a
              href="/app/widgets"
              className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-[#2563EB] hover:underline"
            >
              Open designer <ExternalLink size={14} />
            </a>
          </div>
        </>
      )}
    </div>
  );
}
