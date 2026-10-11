import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Trash2, Check, Loader2, UploadCloud, FileText, Plug, Rocket, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { AGENT_BUILDER } from "@/constants/testIds";

const TABS = [
  { key: "basic", label: "Basic Info" },
  { key: "config", label: "Configuration" },
  { key: "knowledge", label: "Knowledge" },
  { key: "integrations", label: "Integrations" },
  { key: "review", label: "Review & Deploy" },
];
const STEP_ORDER = TABS.map((t) => t.key);

const POSITIONS = ["Bottom Right", "Bottom Left", "Top Right", "Top Left"];

// Purely cosmetic — the real activation call resolves independently; this
// just gives the user something reassuring to watch instead of a blank wait.
const DEPLOY_STEPS = [
  { icon: Sparkles, label: "Saving your configuration" },
  { icon: Rocket, label: "Activating the agent" },
  { icon: Plug, label: "Provisioning the chat widget" },
  { icon: Check, label: "Ready to test" },
];

// Only these fields exist on the backend agent schema; UI-only fields are dropped.
const SAVE_FIELDS = [
  "name", "description", "type", "status", "model", "avatar_url", "website_url",
  "system_prompt", "temperature", "voice", "language", "greeting", "max_tokens",
];

function buildPayload(a, overrides = {}) {
  const payload = Object.fromEntries(
    SAVE_FIELDS.filter((k) => a[k] !== undefined && a[k] !== null).map((k) => [k, a[k]])
  );
  return { ...payload, ...overrides };
}

export default function AgentBuilder() {
  const { id } = useParams();
  const nav = useNavigate();
  const [tab, setTab] = useState("basic");
  const [agent, setAgent] = useState(null);
  const [saveState, setSaveState] = useState("idle"); // idle | saving | saved
  const [deploying, setDeploying] = useState(false);
  const [deployStep, setDeployStep] = useState(0);
  const agentRef = useRef(null);
  const saveTimer = useRef(null);
  const savedTimer = useRef(null);
  const tabInitialized = useRef(false);
  const [models, setModels] = useState([]);

  useEffect(() => {
    api.get(`/agents/${id}`).then((r) => setAgent(r.data)).catch(() => {
      toast.error("Agent not found");
      nav("/app/agents");
    });
  }, [id, nav]);

  // Model picker options — reflects whatever the admin has enabled for this
  // org's plan. Adding a model to the backend catalogue makes it appear here.
  useEffect(() => {
    api.get("/agents/models").then((r) => setModels(r.data?.models || [])).catch(() => setModels([]));
  }, []);

  // An agent that's already configured (or live) shouldn't reopen on Basic
  // Info as if setup never happened — land on the review/deploy summary.
  useEffect(() => {
    if (!agent || tabInitialized.current) return;
    tabInitialized.current = true;
    const configured = Boolean((agent.name || "").trim()) && Boolean((agent.system_prompt || "").trim());
    if (agent.status === "active" || configured) setTab("review");
  }, [agent]);

  // Keep a live ref so the debounced autosave always reads the latest edits.
  useEffect(() => {
    agentRef.current = agent;
  });

  useEffect(
    () => () => {
      clearTimeout(saveTimer.current);
      clearTimeout(savedTimer.current);
    },
    []
  );

  if (!agent) return <div className="h-64 rounded-2xl skeleton" />;

  // Autosave — every edit schedules a debounced silent save with a subtle
  // Saving… / Saved indicator (replaces the manual Save button).
  const autosave = async () => {
    const a = agentRef.current;
    if (!a) return;
    setSaveState("saving");
    try {
      await api.put(`/agents/${id}`, buildPayload(a));
      setSaveState("saved");
      clearTimeout(savedTimer.current);
      savedTimer.current = setTimeout(() => setSaveState("idle"), 2000);
    } catch (err) {
      setSaveState("idle");
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const scheduleSave = () => {
    clearTimeout(saveTimer.current);
    setSaveState("saving");
    saveTimer.current = setTimeout(autosave, 900);
  };

  const set = (key, value) => {
    setAgent((prev) => ({ ...prev, [key]: value }));
    scheduleSave();
  };

  // Deploying an agent flips it to Active — no separate "Start" step. The
  // backend refuses activation until the agent is ready (has a system prompt).
  // Already-active agents skip straight to Channels & Deploy instead of
  // re-submitting the same activation request.
  const deploy = async () => {
    if (agentRef.current?.status === "active") {
      nav(`/app/agents/${id}/deploy`);
      return;
    }
    const previousStatus = agentRef.current?.status;
    const a = { ...agentRef.current, status: "active" };
    setDeploying(true);
    setDeployStep(0);
    const stepTimer = setInterval(() => {
      setDeployStep((s) => Math.min(s + 1, DEPLOY_STEPS.length - 2));
    }, 550);
    try {
      const { data } = await api.put(`/agents/${id}`, buildPayload(a, { status: "active" }));
      setAgent((prev) => ({ ...prev, ...data }));
      clearInterval(stepTimer);
      setDeployStep(DEPLOY_STEPS.length - 1);
      toast.success("Agent deployed — now Active");
      if ((a.website_url || "").trim()) {
        toast.success("Crawling your website — content will appear in Knowledge Base shortly.", { duration: 6000 });
      }
      setTimeout(() => nav(`/app/agents/${id}/deploy`), 700);
    } catch (err) {
      clearInterval(stepTimer);
      setDeploying(false);
      setAgent((prev) => ({ ...prev, status: previousStatus }));
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  // Step gating — Basic Info must be filled before advancing to later steps.
  const stepValid = (key) => {
    if (key === "basic") return Boolean((agent.name || "").trim()) && Boolean((agent.system_prompt || "").trim());
    return true;
  };
  const canReach = (key) => {
    const target = STEP_ORDER.indexOf(key);
    for (let j = 0; j < target; j += 1) if (!stepValid(STEP_ORDER[j])) return false;
    return true;
  };
  const onTab = (key) => {
    if (!canReach(key)) {
      toast.error("Complete the previous step first.");
      return;
    }
    setTab(key);
  };
  const goNext = () => {
    if (!stepValid(tab)) {
      toast.error("Please complete this step before continuing.");
      return;
    }
    const i = STEP_ORDER.indexOf(tab);
    if (i < STEP_ORDER.length - 1) setTab(STEP_ORDER[i + 1]);
  };
  const goBack = () => {
    const i = STEP_ORDER.indexOf(tab);
    if (i > 0) setTab(STEP_ORDER[i - 1]);
  };

  const remove = async () => {
    if (!window.confirm(`Delete "${agent.name}"?`)) return;
    try {
      await api.delete(`/agents/${id}`);
      toast.success("Agent deleted");
      nav("/app/agents");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  return (
    <div>
      <button onClick={() => nav("/app/agents")} className="text-sm text-[#64748B] hover:text-[#0F172A] inline-flex items-center gap-1.5 mb-4">
        <ArrowLeft size={14} /> Back to Agents
      </button>

      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[#0F172A]">{agent.name}</h2>
          <p className="text-sm text-[#64748B] mt-0.5 capitalize">{agent.type} Agent · {agent.status}</p>
        </div>
        <div className="flex items-center gap-3">
          <SaveStatus state={saveState} />
          <button onClick={remove} className="px-4 py-2 rounded-xl border border-[#E2E8F0] hover:bg-red-50 hover:border-red-200 text-red-600 text-sm font-medium inline-flex items-center gap-1.5">
            <Trash2 size={14} /> Delete
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Side tabs */}
        <aside className="lg:col-span-3">
          <div className="p-3 rounded-2xl bg-white border border-[#E2E8F0]">
            <nav className="space-y-1">
              {TABS.map((t, idx) => {
                const reachable = canReach(t.key);
                const isActive = tab === t.key;
                const completed = stepValid(t.key) && STEP_ORDER.indexOf(tab) > idx;
                return (
                  <button
                    key={t.key}
                    onClick={() => onTab(t.key)}
                    data-tour={t.key === "review" ? "builder-tab-review" : undefined}
                    className={`w-full text-left px-3 py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center gap-2 ${
                      isActive
                        ? "bg-[#EFF6FF] text-[#2563EB]"
                        : reachable
                        ? "text-[#475569] hover:bg-[#F8FAFC]"
                        : "text-[#CBD5E1] cursor-not-allowed"
                    }`}
                    data-testid={`builder-tab-${t.key}`}
                  >
                    <span className={`size-6 rounded-full grid place-items-center text-xs font-semibold ${completed ? "bg-[#16A34A] text-white" : isActive ? "bg-[#2563EB] text-white" : reachable ? "bg-[#F1F5F9] text-[#64748B]" : "bg-[#F1F5F9] text-[#CBD5E1]"}`}>
                      {completed ? <Check size={14} /> : idx + 1}
                    </span>
                    {t.label}
                  </button>
                );
              })}
            </nav>
          </div>
        </aside>

        {/* Form panel */}
        <div className="lg:col-span-9">
          <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="p-6 sm:p-8 rounded-2xl bg-white border border-[#E2E8F0]">
            {tab === "basic" && (
              <div className="space-y-5">
                <h3 className="text-lg font-semibold text-[#0F172A]">Basic Information</h3>
                <Field label="Agent Name"><input className="input" value={agent.name || ""} onChange={(e) => set("name", e.target.value)} data-testid={AGENT_BUILDER.nameInput} data-tour="agent-name-input" /></Field>
                <Field label="Business Name"><input className="input" value={agent.business_name || ""} onChange={(e) => set("business_name", e.target.value)} placeholder="Your business name" /></Field>
                <Field label="Purpose"><textarea rows={4} className="input" value={agent.system_prompt || ""} onChange={(e) => set("system_prompt", e.target.value)} placeholder="Handle incoming calls, book appointments and answer FAQs." /></Field>
              </div>
            )}
            {tab === "config" && agent.type === "chat" && (
              <div className="space-y-5">
                <h3 className="text-lg font-semibold text-[#0F172A]">Chat Configuration</h3>
                <ModelField agent={agent} models={models} onChange={(v) => set("model", v)} />
                <Field label="Website URL">
                  <input className="input" value={agent.website_url || ""} onChange={(e) => set("website_url", e.target.value)} placeholder="https://yourwebsite.com" />
                  <p className="mt-1.5 text-[12.5px] text-[#64748B]">We'll automatically crawl this site into your Knowledge Base when you deploy, so the agent answers from your real content.</p>
                </Field>
                <div className="grid sm:grid-cols-2 gap-5">
                  <Field label="Widget Position">
                    <select className="input" value={agent.widget_position || "Bottom Right"} onChange={(e) => set("widget_position", e.target.value)}>
                      {POSITIONS.map((p) => <option key={p}>{p}</option>)}
                    </select>
                  </Field>
                  <Field label="Theme Color"><input type="color" className="h-12 w-full rounded-xl border border-[#E2E8F0]" value={agent.theme_color || "#2563EB"} onChange={(e) => set("theme_color", e.target.value)} /></Field>
                </div>
                <Field label="Welcome Message"><textarea rows={3} className="input" value={agent.greeting || ""} onChange={(e) => set("greeting", e.target.value)} placeholder="Hi! How can I help you today?" /></Field>
              </div>
            )}
            {tab === "config" && agent.type === "whatsapp" && (
              <div className="space-y-5">
                <h3 className="text-lg font-semibold text-[#0F172A]">WhatsApp Configuration</h3>
                <ModelField agent={agent} models={models} onChange={(v) => set("model", v)} />
                <Field label="WhatsApp Number"><input className="input" value={agent.whatsapp_number || ""} onChange={(e) => set("whatsapp_number", e.target.value)} placeholder="+91 98765 43210" /></Field>
                <Field label="Welcome Message"><textarea rows={3} className="input" value={agent.greeting || ""} onChange={(e) => set("greeting", e.target.value)} placeholder="Hello! How can I assist you today?" /></Field>
                <Field label="Business Hours">
                  <select className="input" value={agent.business_hours || "24/7"} onChange={(e) => set("business_hours", e.target.value)}>
                    <option>24/7</option>
                    <option>9 AM - 6 PM (Mon-Fri)</option>
                  </select>
                </Field>
              </div>
            )}
            {tab === "knowledge" && <KnowledgeStep agentName={agent.name} />}
            {tab === "integrations" && <IntegrationsStep />}
            {tab === "review" && (
              <div>
                <h3 className="text-lg font-semibold text-[#0F172A]">Review & Deploy</h3>
                <p className="text-sm text-[#64748B] mt-1">Make sure everything looks good before going live.</p>
                <div className="mt-6 grid sm:grid-cols-2 gap-4 text-sm">
                  <Row label="Name" value={agent.name} />
                  <Row label="Type" value={agent.type} />
                  <Row label="Status" value={agent.status} />
                  <Row label="Business" value={agent.business_name} />
                  {agent.type === "chat" && <><Row label="Website" value={agent.website_url} /><Row label="Position" value={agent.widget_position} /></>}
                  {agent.type === "whatsapp" && <Row label="WhatsApp" value={agent.whatsapp_number} />}
                </div>
                <button
                  onClick={deploy}
                  disabled={deploying}
                  data-tour="agent-deploy-btn"
                  className="mt-6 inline-flex items-center gap-2 px-5 py-3 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold disabled:opacity-70"
                  data-testid="agent-deploy-btn"
                >
                  {deploying ? <Loader2 size={16} className="animate-spin" /> : null}
                  {agent.status === "active" ? "Go to Channels & Deploy →" : "Deploy Agent"}
                </button>
              </div>
            )}

            {/* Step navigation */}
            <div className="mt-8 flex items-center justify-between border-t border-[#F1F5F9] pt-5">
              <button
                onClick={goBack}
                disabled={tab === "basic"}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-[#E2E8F0] text-sm font-medium text-[#475569] hover:bg-[#F8FAFC] disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ArrowLeft size={14} /> Back
              </button>
              {tab !== "review" && (
                <button
                  onClick={goNext}
                  disabled={!stepValid(tab)}
                  data-testid="builder-next-btn"
                  className="inline-flex items-center gap-1.5 px-5 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next <ArrowRight size={14} />
                </button>
              )}
            </div>
          </motion.div>
        </div>
      </div>

      <style>{`
        .input { width: 100%; border-radius: 0.75rem; border: 1px solid #E2E8F0; background: white; padding: 0.75rem 1rem; font-size: 0.875rem; color: #0F172A; }
        .input:focus { outline: none; border-color: #2563EB; box-shadow: 0 0 0 4px rgba(37,99,235,0.1); }
      `}</style>

      <AnimatePresence>
        {deploying && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 grid place-items-center bg-[#0F172A]/50 backdrop-blur-sm"
          >
            <motion.div
              initial={{ opacity: 0, y: 12, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className="w-[90vw] max-w-sm rounded-2xl bg-white p-6 shadow-2xl"
            >
              <p className="text-sm font-bold text-[#0F172A]">Deploying your agent…</p>
              <div className="mt-5 space-y-3">
                {DEPLOY_STEPS.map((s, i) => {
                  const Icon = s.icon;
                  const done = i < deployStep;
                  const active = i === deployStep;
                  return (
                    <div key={s.label} className="flex items-center gap-3">
                      <span
                        className={`grid size-8 shrink-0 place-items-center rounded-full ${
                          done ? "bg-[#DCFCE7] text-[#16A34A]" : active ? "bg-[#EFF4FF] text-[#2563EB]" : "bg-[#F1F5F9] text-[#CBD5E1]"
                        }`}
                      >
                        {done ? <Check size={16} /> : active ? <Loader2 size={16} className="animate-spin" /> : <Icon size={15} />}
                      </span>
                      <span className={`text-sm font-medium ${done || active ? "text-[#0F172A]" : "text-[#94A3B8]"}`}>{s.label}</span>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-[#0F172A] mb-1.5">{label}</label>
      {children}
    </div>
  );
}

// Model picker — lists whatever models the org's plan has enabled. If the
// agent's saved model isn't in the list (e.g. legacy), it's still shown so the
// selection never silently changes.
function ModelField({ agent, models, onChange }) {
  const current = agent.model || "gpt-4o-mini";
  const options = models.length ? models : [{ id: current, label: current }];
  const hasCurrent = options.some((m) => m.id === current);
  return (
    <Field label="AI Model">
      <select className="input" value={current} onChange={(e) => onChange(e.target.value)} data-testid="agent-model-select">
        {!hasCurrent && <option value={current}>{current}</option>}
        {options.map((m) => (
          <option key={m.id} value={m.id}>
            {m.label}{m.provider ? ` · ${m.provider}` : ""}
          </option>
        ))}
      </select>
      <p className="mt-1.5 text-[12.5px] text-[#64748B]">Choose the model that powers this agent. You can change it any time.</p>
    </Field>
  );
}

function Row({ label, value }) {
  return (
    <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
      <p className="text-xs text-[#64748B]">{label}</p>
      <p className="text-sm font-medium text-[#0F172A] mt-0.5">{value || "—"}</p>
    </div>
  );
}

// Subtle autosave indicator — replaces the explicit Save button.
function SaveStatus({ state }) {
  if (state === "saving")
    return (
      <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#64748B]" data-testid="agent-save-status">
        <Loader2 size={13} className="animate-spin" /> Saving…
      </span>
    );
  if (state === "saved")
    return (
      <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#16A34A]" data-testid="agent-save-status">
        <Check size={13} /> Saved
      </span>
    );
  return <span className="text-[12px] font-medium text-[#94A3B8] select-none" data-testid="agent-save-status">Auto-saved</span>;
}

// Knowledge step — upload files inline (no navigation to the Knowledge Base page).
// Files land in a project knowledge base the agent can answer from.
function KnowledgeStep({ agentName }) {
  const [kbs, setKbs] = useState([]);
  const [kbId, setKbId] = useState("");
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [drag, setDrag] = useState(false);
  const inputRef = useRef(null);

  const loadKbs = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/knowledge-bases", { params: { limit: 100 } });
      const items = data.items || [];
      setKbs(items);
      setKbId((cur) => cur || items[0]?.id || "");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDocs = useCallback(async (kb) => {
    if (!kb) {
      setDocs([]);
      return;
    }
    try {
      const { data } = await api.get("/documents", { params: { knowledge_base_id: kb } });
      setDocs(data.items || []);
    } catch {
      setDocs([]);
    }
  }, []);

  useEffect(() => {
    loadKbs();
  }, [loadKbs]);

  useEffect(() => {
    loadDocs(kbId);
  }, [kbId, loadDocs]);

  const ensureKb = async () => {
    if (kbId) return kbId;
    const { data } = await api.post("/knowledge-bases", { name: `${agentName || "Agent"} Knowledge` });
    setKbs((p) => [data, ...p]);
    setKbId(data.id);
    return data.id;
  };

  const upload = async (files) => {
    const list = Array.from(files || []);
    if (!list.length) return;
    setUploading(true);
    try {
      const target = await ensureKb();
      for (const f of list) {
        const fd = new FormData();
        fd.append("knowledge_base_id", target);
        fd.append("file", f);
        await api.post("/documents/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      }
      toast.success(`Added ${list.length} file${list.length > 1 ? "s" : ""}`);
      loadDocs(target);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setUploading(false);
    }
  };

  const removeDoc = async (doc) => {
    try {
      await api.delete(`/documents/${doc.id}`);
      loadDocs(kbId);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-semibold text-[#0F172A]">Knowledge Source</h3>
        <p className="text-sm text-[#64748B] mt-1">Upload documents your agent will answer from. Files are added right here.</p>
      </div>

      {kbs.length > 1 && (
        <Field label="Add files to">
          <select className="input" value={kbId} onChange={(e) => setKbId(e.target.value)}>
            {kbs.map((kb) => (
              <option key={kb.id} value={kb.id}>{kb.name}</option>
            ))}
          </select>
        </Field>
      )}

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          upload(e.dataTransfer.files);
        }}
        className={`p-10 rounded-2xl border border-dashed text-center transition-colors ${drag ? "border-[#2563EB] bg-[#EFF6FF]" : "border-[#CBD5E1] bg-[#F8FAFC]"}`}
      >
        <UploadCloud size={28} className="mx-auto text-[#94A3B8]" />
        <p className="text-sm text-[#475569] mt-3">Drag &amp; drop PDF, DOCX or TXT files here</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            upload(e.target.files);
            e.target.value = "";
          }}
          data-testid="agent-knowledge-input"
        />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm disabled:opacity-60"
        >
          {uploading ? <Loader2 size={14} className="animate-spin" /> : <UploadCloud size={14} />}
          {uploading ? "Uploading…" : "Choose files"}
        </button>
      </div>

      {loading ? (
        <div className="h-16 rounded-xl skeleton" />
      ) : docs.length > 0 ? (
        <div className="space-y-2">
          {docs.map((d) => (
            <div key={d.id} className="flex items-center gap-3 p-3 rounded-xl border border-[#E2E8F0] bg-white">
              <FileText size={16} className="text-[#64748B] shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[#0F172A] truncate">{d.filename}</p>
                <p className="text-xs text-[#94A3B8] capitalize">{d.status}</p>
              </div>
              <button onClick={() => removeDoc(d)} className="p-1.5 rounded-lg text-[#94A3B8] hover:text-red-600 hover:bg-red-50">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

// Integrations step — connect tools inline (no navigation to the Integrations page).
function IntegrationsStep() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/integrations");
      setEntries(data.items || []);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const connect = async (provider) => {
    setBusy((p) => ({ ...p, [provider]: true }));
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
      setBusy((p) => ({ ...p, [provider]: false }));
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-lg font-semibold text-[#0F172A]">Integrations</h3>
        <p className="text-sm text-[#64748B] mt-1">Connect tools your agent will use — right here.</p>
      </div>

      {loading ? (
        <div className="h-24 rounded-xl skeleton" />
      ) : (
        <div className="grid sm:grid-cols-2 gap-3">
          {entries.map((e) => {
            const provider = e.catalog.provider;
            const connected = e.integration && e.integration.status !== "disconnected";
            return (
              <div key={provider} className="flex items-center gap-3 p-3 rounded-xl border border-[#E2E8F0] bg-white">
                <span className="size-9 rounded-xl grid place-items-center bg-[#F1F5F9] shrink-0">
                  <Plug size={16} style={{ color: e.catalog.color || "#64748B" }} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-[#0F172A] truncate">{e.catalog.name}</p>
                  <p className="text-xs text-[#94A3B8] truncate">{e.catalog.description}</p>
                </div>
                {connected ? (
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#16A34A] shrink-0">
                    <Check size={13} /> Connected
                  </span>
                ) : (
                  <button
                    onClick={() => connect(provider)}
                    disabled={busy[provider]}
                    className="px-3 py-1.5 rounded-lg border border-[#E2E8F0] hover:bg-[#F8FAFC] text-xs font-semibold text-[#0F172A] disabled:opacity-60 shrink-0"
                  >
                    {busy[provider] ? "…" : "Connect"}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
