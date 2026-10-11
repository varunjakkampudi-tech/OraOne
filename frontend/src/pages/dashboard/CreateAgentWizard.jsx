import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Globe,
  LifeBuoy,
  BookOpen,
  TrendingUp,
  MessageCircle,
  Code2,
  Upload,
  FileText,
  Plug,
  SkipForward,
  ArrowLeft,
  ArrowRight,
  Check,
  Copy,
  Loader2,
  Cpu,
  Rocket,
  Database,
  LayoutGrid,
  Brain,
  Clock,
  DollarSign,
  X,
} from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";

/**
 * Create AI Agent — a single guided journey.
 *
 * The user expresses a GOAL, points us at a SOURCE to learn from, picks a
 * MODEL, customizes the personality, and DEPLOYS — all without ever opening
 * Knowledge Base, Websites, Widgets or Integrations directly. OraOne wires the
 * underlying resources (knowledge base, crawl/upload, agent, widget) behind the
 * scenes using the existing APIs.
 */

const GOALS = [
  {
    id: "website",
    type: "chat",
    icon: Globe,
    color: "#2563EB",
    title: "Website Chatbot",
    desc: "Answer visitor questions on your site.",
    prompt:
      "You are a helpful website assistant. Answer visitor questions accurately using the provided knowledge. Be concise and friendly, and if you don't know, offer to connect them with the team.",
  },
  {
    id: "support",
    type: "chat",
    icon: LifeBuoy,
    color: "#0EA5E9",
    title: "Customer Support",
    desc: "Resolve support questions and FAQs.",
    prompt:
      "You are a customer support agent. Help customers resolve issues using the knowledge base. Be empathetic, clear, and solution-oriented.",
  },
  {
    id: "internal",
    type: "chat",
    icon: BookOpen,
    color: "#0891B2",
    title: "Internal Knowledge",
    desc: "Answer your team's internal questions.",
    prompt:
      "You are an internal knowledge assistant for employees. Answer questions from internal documentation accurately and reference relevant policies.",
  },
  {
    id: "sales",
    type: "chat",
    icon: TrendingUp,
    color: "#10B981",
    title: "Sales Assistant",
    desc: "Qualify leads and answer product questions.",
    prompt:
      "You are a sales assistant. Engage visitors, answer product questions persuasively, and capture lead details when there is genuine interest.",
  },
  {
    id: "api",
    type: "chat",
    icon: Code2,
    color: "#64748B",
    title: "API Assistant",
    desc: "Serve AI answers through the API.",
    prompt:
      "You are an API-accessible assistant. Provide accurate, well-structured answers grounded in the knowledge base.",
  },
];

const SOURCES = [
  { id: "website", icon: Globe, title: "Crawl a Website", desc: "We'll read your site and learn from it." },
  { id: "upload", icon: Upload, title: "Upload Files", desc: "PDF, DOCX, TXT, CSV, and more." },
  { id: "text", icon: FileText, title: "Paste Text", desc: "Paste content directly." },
  { id: "integration", icon: Plug, title: "Connect an App", desc: "Google Drive, Notion, and more." },
  { id: "skip", icon: SkipForward, title: "Skip for now", desc: "Add knowledge later." },
];

const PROVIDERS = [
  { id: "google_drive", label: "Google Drive", color: "#1A73E8" },
  { id: "notion", label: "Notion", color: "#0F172A" },
  { id: "confluence", label: "Confluence", color: "#1868DB" },
  { id: "sharepoint", label: "SharePoint", color: "#038387" },
];

const TONES = [
  { id: "friendly", label: "Friendly", temperature: 0.8 },
  { id: "professional", label: "Professional", temperature: 0.5 },
  { id: "concise", label: "Concise", temperature: 0.3 },
  { id: "playful", label: "Playful", temperature: 1.0 },
];

const STEPS = ["Goal", "Knowledge Sources", "Refine", "Model", "Customize", "Deploy"];

const inputCls =
  "w-full rounded-xl border border-[#E2E8F0] bg-white px-3.5 py-2.5 text-sm text-[#0F172A] placeholder:text-[#94A3B8] focus:border-[#2563EB] focus:ring-2 focus:ring-[#2563EB]/15 outline-none transition";

export default function CreateAgentWizard() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [goal, setGoal] = useState(null);

  // Knowledge source
  const [sourceKind, setSourceKind] = useState(null);
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  const [provider, setProvider] = useState(null);
  const [kbId, setKbId] = useState(null);
  const [committingSource, setCommittingSource] = useState(false);
  const fileRef = useRef(null);

  // Refine — clarifying questions (Claude-Opus style: option chips + final prompt)
  const [clarify, setClarify] = useState(null); // { intro, questions, final_label, final_placeholder }
  const [clarifyLoading, setClarifyLoading] = useState(false);
  const [answers, setAnswers] = useState({}); // { questionId: [optionLabel, ...] }
  const [extra, setExtra] = useState("");
  const appliedRefRef = useRef("");

  // Model
  const [models, setModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [model, setModel] = useState("");

  // Customize
  const [form, setForm] = useState({
    name: "",
    greeting: "Hi! How can I help you today?",
    systemPrompt: "",
    tone: "friendly",
    language: "en-US",
  });

  // Deploy
  const [deploying, setDeploying] = useState(false);
  const [result, setResult] = useState(null); // { agent, widget }
  const [copied, setCopied] = useState(false);

  // Load models when reaching the model step
  useEffect(() => {
    if (step !== 3 || models.length) return;
    let active = true;
    (async () => {
      setModelsLoading(true);
      try {
        const { data } = await api.get("/ai/models");
        if (!active) return;
        const list = (data?.models || []).filter((m) => m.enabled && m.entitled && !m.disabled_by_org);
        setModels(list);
        setModel((prev) => prev || data?.default_model || list[0]?.id || "");
      } catch (err) {
        toast.error(formatApiError(err.response?.data?.detail));
      } finally {
        if (active) setModelsLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [step, models.length]);

  // Generate clarifying questions when reaching the Refine step
  useEffect(() => {
    if (step !== 2 || clarify) return;
    let active = true;
    (async () => {
      setClarifyLoading(true);
      try {
        const { data } = await api.post("/ai/clarify", {
          goal_id: goal?.id,
          goal_type: goal?.type,
          goal_title: goal?.title,
          source_kind: sourceKind,
          knowledge_base_id: kbId || undefined,
        });
        if (active) setClarify(data);
      } catch (err) {
        if (active) toast.error(formatApiError(err.response?.data?.detail));
      } finally {
        if (active) setClarifyLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [step, clarify, goal, sourceKind, kbId]);

  const chooseGoal = (g) => {
    setGoal(g);
    setForm((f) => ({
      ...f,
      name: f.name || `${g.title}`,
      systemPrompt: f.systemPrompt || g.prompt,
    }));
  };

  const kbName = useMemo(
    () => `${form.name || goal?.title || "Agent"} Knowledge`.slice(0, 160),
    [form.name, goal]
  );

  // Fold the clarifying answers into the agent's system prompt so the user sees
  // and can tweak the result in the Customize step. Re-applying replaces the
  // previous refinement block rather than stacking duplicates.
  const applyRefinement = () => {
    const lines = [];
    for (const q of clarify?.questions || []) {
      const sel = answers[q.id];
      if (sel && sel.length) lines.push(`- ${q.question} → ${sel.join(", ")}`);
    }
    let block = "";
    if (lines.length) block += `\n\nBehaviour guidelines:\n${lines.join("\n")}`;
    if (extra.trim()) block += `\n\nAdditional instructions: ${extra.trim()}`;

    setForm((f) => {
      let sp = f.systemPrompt || "";
      if (appliedRefRef.current && sp.includes(appliedRefRef.current)) {
        sp = sp.replace(appliedRefRef.current, "");
      }
      appliedRefRef.current = block;
      return { ...f, systemPrompt: (sp.trimEnd() + block).trim() };
    });
  };

  // Create the knowledge base + attach the chosen source. Runs when leaving
  // the Knowledge step so crawling/processing happens while the user finishes.
  const commitSource = async () => {
    if (!sourceKind || sourceKind === "skip") return true;
    if (kbId) return true; // already created in a previous pass

    // Validate the chosen source before doing any work
    if (sourceKind === "website" && !url.trim()) {
      toast.error("Enter a website URL to crawl.");
      return false;
    }
    if (sourceKind === "upload" && files.length === 0) {
      toast.error("Choose at least one file to upload.");
      return false;
    }
    if (sourceKind === "text" && !text.trim()) {
      toast.error("Paste some text first.");
      return false;
    }
    if (sourceKind === "integration" && !provider) {
      toast.error("Pick an app to connect.");
      return false;
    }

    setCommittingSource(true);
    try {
      const { data: kb } = await api.post("/knowledge-bases", {
        name: kbName,
        description: `Auto-created for the ${goal?.title || "agent"} journey.`,
        status: "active",
      });
      setKbId(kb.id);

      if (sourceKind === "website") {
        await api.post("/websites?start=true", {
          knowledge_base_id: kb.id,
          base_url: url.trim(),
          name: url.trim(),
          crawl_mode: "entire",
        });
        toast.success("Crawl started — your site is being indexed.");
      } else if (sourceKind === "upload") {
        for (const file of files) {
          const fd = new FormData();
          fd.append("knowledge_base_id", kb.id);
          fd.append("file", file);
          await api.post("/documents/upload", fd, {
            headers: { "Content-Type": "multipart/form-data" },
          });
        }
        toast.success(`${files.length} file${files.length > 1 ? "s" : ""} uploaded.`);
      } else if (sourceKind === "text") {
        const blob = new File([text.trim()], "pasted-content.txt", { type: "text/plain" });
        const fd = new FormData();
        fd.append("knowledge_base_id", kb.id);
        fd.append("file", blob);
        await api.post("/documents/upload", fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        toast.success("Text added to knowledge.");
      } else if (sourceKind === "integration") {
        await api.post("/integrations/connect", { provider, mock: true });
        toast.success(`${PROVIDERS.find((p) => p.id === provider)?.label || "App"} connected.`);
      }
      return true;
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
      setKbId(null);
      return false;
    } finally {
      setCommittingSource(false);
    }
  };

  const next = async () => {
    if (step === 0 && !goal) {
      toast.error("Pick what you want your AI to do.");
      return;
    }
    if (step === 1) {
      const ok = await commitSource();
      if (!ok) return;
    }
    if (step === 2) {
      applyRefinement();
    }
    if (step === 4 && !form.name.trim()) {
      toast.error("Give your agent a name.");
      return;
    }
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };

  const back = () => setStep((s) => Math.max(s - 1, 0));

  const deploy = async () => {
    if (!goal) return;
    setDeploying(true);
    try {
      const tone = TONES.find((t) => t.id === form.tone) || TONES[0];
      const { data: agent } = await api.post("/agents", {
        name: form.name.trim(),
        type: goal.type,
        description: goal.desc,
        model: model || undefined,
        status: "active",
        system_prompt: form.systemPrompt.trim() || goal.prompt,
        greeting: form.greeting.trim(),
        temperature: tone.temperature,
        language: form.language,
      });

      let widget = null;
      if (goal.type === "chat") {
        const { data: w } = await api.post("/widgets", {
          name: `${form.name.trim()} Widget`,
          agent_id: agent.id,
          knowledge_base_id: kbId || undefined,
          widget_type: "bubble",
          position: "bottom-right",
          settings: {
            agent_name: form.name.trim(),
            welcome_message: form.greeting.trim(),
          },
        });
        try {
          const { data: pub } = await api.post(`/widgets/${w.id}/publish?publish=true`);
          widget = pub;
        } catch {
          widget = w; // created but not published — still usable
        }
      }

      setResult({ agent, widget });
      setStep(STEPS.length - 1);
      toast.success("Your AI agent is live!");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setDeploying(false);
    }
  };

  const copySnippet = async () => {
    const snippet = result?.widget?.embed_snippet;
    if (!snippet) return;
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Couldn't copy — select and copy manually.");
    }
  };

  return (
    <div className="mx-auto max-w-5xl p-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid size-11 place-items-center rounded-2xl bg-gradient-to-br from-[#2563EB] to-[#06B6D4] text-white shadow-sm">
            <Sparkles size={22} />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[#0F172A]">Create your AI agent</h1>
            <p className="text-sm text-[#64748B]">
              One guided journey — we'll set up everything behind the scenes.
            </p>
          </div>
        </div>
        <button
          onClick={() => nav("/app/dashboard")}
          className="rounded-lg p-2 text-[#64748B] hover:bg-[#F1F5F9] hover:text-[#0F172A]"
          aria-label="Close"
        >
          <X size={18} />
        </button>
      </div>

      {/* Stepper */}
      <div className="mt-6 flex items-center gap-2">
        {STEPS.map((label, i) => {
          const done = i < step || result;
          const current = i === step && !result;
          return (
            <React.Fragment key={label}>
              <div className="flex items-center gap-2">
                <div
                  className={`grid size-7 place-items-center rounded-full text-xs font-semibold transition-colors ${
                    done
                      ? "bg-[#10B981] text-white"
                      : current
                      ? "bg-[#2563EB] text-white"
                      : "bg-[#E2E8F0] text-[#64748B]"
                  }`}
                >
                  {done ? <Check size={14} /> : i + 1}
                </div>
                <span
                  className={`hidden text-sm font-medium sm:inline ${
                    current ? "text-[#0F172A]" : "text-[#94A3B8]"
                  }`}
                >
                  {label}
                </span>
              </div>
              {i < STEPS.length - 1 && <div className="h-px flex-1 bg-[#E2E8F0]" />}
            </React.Fragment>
          );
        })}
      </div>

      {/* Body */}
      <div className="mt-8 rounded-3xl border border-[#E2E8F0] bg-white p-6 shadow-sm">
        <AnimatePresence mode="wait">
          <motion.div
            key={result ? "done" : step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            {result ? (
              <DeployedView result={result} goal={goal} copied={copied} onCopy={copySnippet} nav={nav} />
            ) : step === 0 ? (
              <StepGoal goal={goal} onChoose={chooseGoal} />
            ) : step === 1 ? (
              <StepKnowledge
                sourceKind={sourceKind}
                setSourceKind={setSourceKind}
                url={url}
                setUrl={setUrl}
                text={text}
                setText={setText}
                files={files}
                setFiles={setFiles}
                provider={provider}
                setProvider={setProvider}
                fileRef={fileRef}
              />
            ) : step === 2 ? (
              <StepRefine
                loading={clarifyLoading}
                clarify={clarify}
                answers={answers}
                setAnswers={setAnswers}
                extra={extra}
                setExtra={setExtra}
              />
            ) : step === 3 ? (
              <StepModel
                models={models}
                loading={modelsLoading}
                model={model}
                setModel={setModel}
              />
            ) : step === 4 ? (
              <StepCustomize form={form} setForm={setForm} />
            ) : (
              <StepDeploy goal={goal} form={form} kbId={kbId} sourceKind={sourceKind} model={model} url={url} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Footer nav */}
      {!result && (
        <div className="mt-6 flex items-center justify-between">
          <button
            onClick={back}
            disabled={step === 0}
            className="inline-flex items-center gap-1.5 rounded-xl px-4 py-2.5 text-sm font-medium text-[#475569] hover:bg-[#F1F5F9] disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ArrowLeft size={16} /> Back
          </button>

          {step < STEPS.length - 1 ? (
            <button
              onClick={next}
              disabled={committingSource}
              className="inline-flex items-center gap-1.5 rounded-full bg-[#2563EB] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#1D4ED8] disabled:opacity-60"
            >
              {committingSource ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Setting up…
                </>
              ) : (
                <>
                  Continue <ArrowRight size={16} />
                </>
              )}
            </button>
          ) : (
            <button
              onClick={deploy}
              disabled={deploying}
              className="inline-flex items-center gap-1.5 rounded-full bg-[#2563EB] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#1D4ED8] disabled:opacity-60"
            >
              {deploying ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Deploying…
                </>
              ) : (
                <>
                  <Rocket size={16} /> Deploy agent
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------- Steps --------------------------------- */

function StepGoal({ goal, onChoose }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-[#0F172A]">What do you want your AI to do?</h2>
      <p className="mt-1 text-sm text-[#64748B]">Pick a goal — no technical setup required.</p>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {GOALS.map((g) => {
          const active = goal?.id === g.id;
          return (
            <button
              key={g.id}
              onClick={() => onChoose(g)}
              className={`flex items-start gap-3 rounded-2xl border-2 p-4 text-left transition-all ${
                active ? "border-[#2563EB] bg-[#EFF6FF]" : "border-[#E2E8F0] bg-white hover:border-[#CBD5E1]"
              }`}
            >
              <div className="grid size-10 shrink-0 place-items-center rounded-xl" style={{ background: `${g.color}15` }}>
                <g.icon size={18} style={{ color: g.color }} />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-[#0F172A]">{g.title}</p>
                <p className="mt-0.5 text-xs text-[#64748B]">{g.desc}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function StepKnowledge({
  sourceKind,
  setSourceKind,
  url,
  setUrl,
  text,
  setText,
  files,
  setFiles,
  provider,
  setProvider,
  fileRef,
}) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-[#0F172A]">Where should it learn from?</h2>
      <p className="mt-1 text-sm text-[#64748B]">
        Choose a source — we'll build and index the knowledge for you.
      </p>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {SOURCES.map((s) => {
          const active = sourceKind === s.id;
          return (
            <button
              key={s.id}
              onClick={() => setSourceKind(s.id)}
              className={`flex items-start gap-3 rounded-2xl border-2 p-4 text-left transition-all ${
                active ? "border-[#2563EB] bg-[#EFF6FF]" : "border-[#E2E8F0] bg-white hover:border-[#CBD5E1]"
              }`}
            >
              <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-[#F1F5F9]">
                <s.icon size={18} className="text-[#2563EB]" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-[#0F172A]">{s.title}</p>
                <p className="mt-0.5 text-xs text-[#64748B]">{s.desc}</p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Source-specific inputs */}
      <div className="mt-5">
        {sourceKind === "website" && (
          <div>
            <label className="mb-1.5 block text-sm font-medium text-[#0F172A]">Website URL</label>
            <input
              className={inputCls}
              placeholder="https://yourcompany.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <p className="mt-1.5 text-xs text-[#94A3B8]">
              We'll crawl your site and turn its pages into answerable knowledge.
            </p>
          </div>
        )}

        {sourceKind === "upload" && (
          <div>
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#CBD5E1] bg-[#F8FAFC] px-4 py-8 text-sm font-medium text-[#64748B] hover:border-[#2563EB] hover:text-[#2563EB]"
            >
              <Upload size={18} /> Click to choose files
            </button>
            <input
              ref={fileRef}
              type="file"
              multiple
              className="hidden"
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
            />
            {files.length > 0 && (
              <ul className="mt-3 space-y-1.5">
                {files.map((f, i) => (
                  <li
                    key={i}
                    className="flex items-center gap-2 rounded-lg bg-[#F1F5F9] px-3 py-2 text-sm text-[#0F172A]"
                  >
                    <FileText size={14} className="text-[#64748B]" />
                    <span className="truncate">{f.name}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {sourceKind === "text" && (
          <div>
            <label className="mb-1.5 block text-sm font-medium text-[#0F172A]">Paste your content</label>
            <textarea
              className={`${inputCls} min-h-[140px] resize-y`}
              placeholder="Paste FAQs, policies, product details…"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>
        )}

        {sourceKind === "integration" && (
          <div>
            <label className="mb-1.5 block text-sm font-medium text-[#0F172A]">Choose an app</label>
            <div className="grid gap-2 sm:grid-cols-2">
              {PROVIDERS.map((p) => {
                const active = provider === p.id;
                return (
                  <button
                    key={p.id}
                    onClick={() => setProvider(p.id)}
                    className={`flex items-center gap-3 rounded-xl border-2 p-3 text-left transition ${
                      active ? "border-[#2563EB] bg-[#EFF6FF]" : "border-[#E2E8F0] hover:border-[#CBD5E1]"
                    }`}
                  >
                    <span
                      className="grid size-8 place-items-center rounded-lg text-xs font-bold text-white"
                      style={{ background: p.color }}
                    >
                      {p.label.slice(0, 1)}
                    </span>
                    <span className="text-sm font-medium text-[#0F172A]">{p.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {sourceKind === "skip" && (
          <p className="rounded-xl bg-[#F8FAFC] px-4 py-3 text-sm text-[#64748B]">
            No problem — you can add knowledge any time after your agent is live.
          </p>
        )}
      </div>
    </div>
  );
}

function StepRefine({ loading, clarify, answers, setAnswers, extra, setExtra }) {
  const toggle = (q, label) => {
    setAnswers((prev) => {
      const cur = prev[q.id] || [];
      if (q.type === "multi") {
        const next = cur.includes(label) ? cur.filter((x) => x !== label) : [...cur, label];
        return { ...prev, [q.id]: next };
      }
      // single-select
      return { ...prev, [q.id]: cur.includes(label) ? [] : [label] };
    });
  };

  if (loading || !clarify) {
    return (
      <div className="flex items-center gap-2 py-10 text-sm text-[#64748B]">
        <Loader2 size={16} className="animate-spin" /> Reviewing your knowledge and preparing a few questions…
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-start gap-3">
        <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-[#EFF6FF] text-[#2563EB]">
          <Sparkles size={18} />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-[#0F172A]">A few quick questions</h2>
          <p className="mt-1 text-sm text-[#64748B]">{clarify.intro}</p>
        </div>
      </div>

      <div className="mt-6 space-y-6">
        {clarify.questions.map((q) => (
          <div key={q.id}>
            <p className="text-sm font-semibold text-[#0F172A]">
              {q.question}
              {q.type === "multi" && (
                <span className="ml-2 text-xs font-normal text-[#64748B]">Choose any</span>
              )}
              {q.optional && (
                <span className="ml-2 text-xs font-normal text-[#64748B]">Optional</span>
              )}
            </p>
            <div className="mt-2.5 flex flex-wrap gap-2">
              {q.options.map((o) => {
                const active = (answers[q.id] || []).includes(o.label);
                return (
                  <button
                    key={o.id}
                    type="button"
                    onClick={() => toggle(q, o.label)}
                    className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm font-medium transition ${
                      active
                        ? "border-[#2563EB] bg-[#2563EB] text-white"
                        : "border-[#E2E8F0] bg-white text-[#475569] hover:border-[#CBD5E1]"
                    }`}
                  >
                    {active && <Check size={14} />}
                    {o.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        <div>
          <label className="block text-sm font-semibold text-[#0F172A]">{clarify.final_label}</label>
          <textarea
            className={`${inputCls} mt-2 min-h-[90px] resize-y`}
            placeholder={clarify.final_placeholder}
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
          />
          <p className="mt-1.5 text-xs text-[#94A3B8]">
            Your answers refine the assistant's system prompt — you can fine-tune it in the next steps.
          </p>
        </div>
      </div>
    </div>
  );
}

function StepModel({ models, loading, model, setModel }) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-[#0F172A]">Choose the AI model</h2>
      <p className="mt-1 text-sm text-[#64748B]">
        Pick the engine that powers your agent. You can change this later.
      </p>

      {loading ? (
        <div className="mt-6 flex items-center gap-2 text-sm text-[#64748B]">
          <Loader2 size={16} className="animate-spin" /> Loading available models…
        </div>
      ) : models.length === 0 ? (
        <p className="mt-6 rounded-xl bg-[#F8FAFC] px-4 py-3 text-sm text-[#64748B]">
          No models available on your plan. The default model will be used.
        </p>
      ) : (
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          {models.map((m) => {
            const active = model === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setModel(m.id)}
                className={`flex items-start gap-3 rounded-2xl border-2 p-4 text-left transition-all ${
                  active ? "border-[#2563EB] bg-[#EFF6FF]" : "border-[#E2E8F0] bg-white hover:border-[#CBD5E1]"
                }`}
              >
                <div className="grid size-10 shrink-0 place-items-center rounded-xl bg-[#F1F5F9]">
                  <Cpu size={18} className="text-[#2563EB]" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-semibold text-[#0F172A]">{m.label || m.id}</p>
                    {active && <Check size={16} className="shrink-0 text-[#2563EB]" />}
                  </div>
                  <p className="mt-0.5 text-xs capitalize text-[#64748B]">{m.provider}</p>
                  {Array.isArray(m.capabilities) && m.capabilities.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {m.capabilities.slice(0, 3).map((c) => (
                        <span
                          key={c}
                          className="rounded-full bg-[#EFF6FF] px-2 py-0.5 text-[10px] font-medium text-[#2563EB]"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StepCustomize({ form, setForm }) {
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  return (
    <div>
      <h2 className="text-lg font-semibold text-[#0F172A]">Customize your agent</h2>
      <p className="mt-1 text-sm text-[#64748B]">Give it a name, a personality, and a greeting.</p>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-[#0F172A]">Name</label>
          <input className={inputCls} value={form.name} onChange={(e) => set("name", e.target.value)} />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-[#0F172A]">Language</label>
          <select className={inputCls} value={form.language} onChange={(e) => set("language", e.target.value)}>
            <option value="en-US">English (US)</option>
            <option value="en-GB">English (UK)</option>
            <option value="es-ES">Spanish</option>
            <option value="fr-FR">French</option>
            <option value="de-DE">German</option>
            <option value="hi-IN">Hindi</option>
            <option value="pt-BR">Portuguese</option>
          </select>
        </div>
      </div>

      <div className="mt-4">
        <label className="mb-1.5 block text-sm font-medium text-[#0F172A]">Greeting</label>
        <input className={inputCls} value={form.greeting} onChange={(e) => set("greeting", e.target.value)} />
      </div>

      <div className="mt-4">
        <label className="mb-1.5 block text-sm font-medium text-[#0F172A]">Tone</label>
        <div className="flex flex-wrap gap-2">
          {TONES.map((t) => (
            <button
              key={t.id}
              onClick={() => set("tone", t.id)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                form.tone === t.id
                  ? "bg-[#2563EB] text-white"
                  : "bg-[#F1F5F9] text-[#475569] hover:bg-[#E2E8F0]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4">
        <label className="mb-1.5 block text-sm font-medium text-[#0F172A]">
          Instructions <span className="font-normal text-[#64748B]">(how it should behave)</span>
        </label>
        <textarea
          className={`${inputCls} min-h-[120px] resize-y`}
          value={form.systemPrompt}
          onChange={(e) => set("systemPrompt", e.target.value)}
        />
      </div>
    </div>
  );
}

function StepDeploy({ goal, form, kbId, sourceKind, model, url }) {
  const isChat = goal?.type === "chat";
  const sourceTitle = SOURCES.find((s) => s.id === sourceKind)?.title;
  const knowledgeValue =
    !sourceKind || sourceKind === "skip"
      ? "None (add later)"
      : kbId
      ? "Connected & indexing"
      : sourceTitle || "Configured";

  let websiteValue = "—";
  if (sourceKind === "website" && url) {
    try {
      websiteValue = new URL(url.startsWith("http") ? url : `https://${url}`).hostname;
    } catch {
      websiteValue = url;
    }
  }

  const modelValue = model || "Plan default";
  const costValue = estimateCost(modelValue);

  // Grouped like a Vercel deployment summary.
  const groups = [
    {
      title: "Agent",
      rows: [
        { label: "Name", value: form.name || goal?.title },
        { label: "Goal", value: goal?.title },
        { label: "Type", value: goal?.type },
        { label: "Tone", value: form.tone },
      ],
    },
    {
      title: "Intelligence",
      rows: [
        { label: "Model", value: modelValue, icon: Cpu },
        { label: "Knowledge", value: knowledgeValue, icon: Database },
        { label: "Website", value: websiteValue, icon: Globe },
        { label: "Estimated cost", value: costValue, icon: DollarSign },
      ],
    },
    {
      title: "Channel & policy",
      rows: [
        { label: "Widget", value: isChat ? "Auto-published" : "Not applicable", icon: LayoutGrid },
        { label: "Memory", value: "Enabled", icon: Brain },
        { label: "Conversation retention", value: "90 days", icon: Clock },
      ],
    },
  ];

  return (
    <div>
      <div className="flex items-center gap-2">
        <Rocket size={18} className="text-[#2563EB]" />
        <h2 className="text-lg font-semibold text-[#0F172A]">Review &amp; deploy</h2>
      </div>
      <p className="mt-1 text-sm text-[#64748B]">
        We'll create the agent{isChat ? ", publish a website widget," : ""} and connect your knowledge —
        all in one click.
      </p>

      <div className="mt-5 space-y-4">
        {groups.map((g) => (
          <div key={g.title} className="overflow-hidden rounded-2xl border border-[#E2E8F0]">
            <p className="border-b border-[#F1F5F9] bg-[#F8FAFC] px-4 py-2 text-[11px] font-bold uppercase tracking-wider text-[#64748B]">
              {g.title}
            </p>
            <dl className="divide-y divide-[#F1F5F9]">
              {g.rows.map((r) => (
                <div key={r.label} className="flex items-center justify-between gap-4 px-4 py-2.5">
                  <dt className="inline-flex items-center gap-2 text-sm text-[#64748B]">
                    {r.icon && <r.icon size={14} className="text-[#94A3B8]" />}
                    {r.label}
                  </dt>
                  <dd className="truncate text-sm font-medium capitalize text-[#0F172A]">
                    {r.value || "—"}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>

      <p className="mt-4 flex items-center gap-1.5 text-xs text-[#94A3B8]">
        <Sparkles size={12} /> Memory, retention and cost use your workspace defaults — adjust them anytime
        from the agent settings.
      </p>
    </div>
  );
}

// Rough per-message cost estimate by model family (USD), for the deploy summary.
function estimateCost(model) {
  const m = String(model || "").toLowerCase();
  if (!m || m === "plan default") return "Usage-based";
  const tiers = [
    ["mini", 0.0006],
    ["nano", 0.0004],
    ["haiku", 0.0008],
    ["flash", 0.0005],
    ["gpt-4o", 0.012],
    ["gpt-4.1", 0.01],
    ["sonnet", 0.011],
    ["opus", 0.05],
    ["gemini", 0.007],
    ["deepseek", 0.0009],
  ];
  for (const [needle, cost] of tiers) {
    if (m.includes(needle)) return `~$${cost.toFixed(4)} / message`;
  }
  return "Usage-based";
}

function DeployedView({ result, goal, copied, onCopy, nav }) {
  const { agent, widget } = result;
  const snippet = widget?.embed_snippet;
  return (
    <div className="text-center">
      <div className="mx-auto grid size-14 place-items-center rounded-2xl bg-[#ECFDF5] text-[#10B981]">
        <Check size={28} />
      </div>
      <h2 className="mt-4 text-xl font-bold text-[#0F172A]">{agent?.name} is live! 🎉</h2>
      <p className="mx-auto mt-1 max-w-md text-sm text-[#64748B]">
        Your agent has been created and activated. {goal?.type === "chat" && snippet
          ? "Drop the snippet below on your website to go live."
          : "Configure its channel from the agent page to start talking to customers."}
      </p>

      {goal?.type === "chat" && snippet && (
        <div className="mt-6 text-left">
          <label className="mb-1.5 block text-sm font-medium text-[#0F172A]">Embed snippet</label>
          <div className="relative">
            <pre className="overflow-x-auto rounded-2xl border border-[#E2E8F0] bg-[#0F172A] p-4 text-xs text-[#E2E8F0]">
              <code>{snippet}</code>
            </pre>
            <button
              onClick={onCopy}
              className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-lg bg-white/10 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-white/20"
            >
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      )}

      <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
        <button
          onClick={() => nav(`/app/agents/${agent.id}`)}
          className="inline-flex items-center gap-1.5 rounded-full bg-[#2563EB] px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[#1D4ED8]"
        >
          Configure agent <ArrowRight size={16} />
        </button>
        <button
          onClick={() => nav("/app/chat")}
          className="inline-flex items-center gap-1.5 rounded-xl border border-[#E2E8F0] px-5 py-2.5 text-sm font-semibold text-[#475569] hover:bg-[#F8FAFC]"
        >
          Test in chat
        </button>
      </div>
    </div>
  );
}
