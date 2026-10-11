import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  FolderKanban,
  Bot,
  BookOpen,
  MessagesSquare,
  Globe,
  CornerDownLeft,
  Loader2,
  LayoutDashboard,
  Plug,
  Users,
} from "lucide-react";
import { api } from "@/lib/api";
import { useProjects } from "@/lib/projects";
import { useEntitlements } from "@/lib/entitlements";

// Static destinations so the palette doubles as fast navigation.
const PAGES = [
  { label: "Dashboard", to: "/app/dashboard", icon: LayoutDashboard, keywords: "home overview dashboard" },
  { label: "AI Agents", to: "/app/agents", icon: Bot, keywords: "bots assistants" },
  { label: "Conversations", to: "/app/conversations", icon: MessagesSquare, keywords: "chats inbox" },
  { label: "Knowledge", to: "/app/knowledge-base", icon: BookOpen, keywords: "docs documents" },
  { label: "Websites", to: "/app/knowledge-base/websites", icon: Globe, keywords: "crawl knowledge" },
  { label: "Integrations", to: "/app/integrations", icon: Plug, keywords: "apps connect" },
  { label: "Leads", to: "/app/leads", icon: Users, keywords: "contacts crm", feature: "crm" },
];

const GROUP_META = {
  pages: { label: "Go to", icon: LayoutDashboard },
  projects: { label: "Projects", icon: FolderKanban },
  agents: { label: "AI Agents", icon: Bot },
  knowledge: { label: "Knowledge", icon: BookOpen },
  conversations: { label: "Conversations", icon: MessagesSquare },
  websites: { label: "Websites", icon: Globe },
};

function normalize(data, keys) {
  if (Array.isArray(data)) return data;
  if (!data) return [];
  for (const k of keys) if (Array.isArray(data[k])) return data[k];
  return [];
}

export default function CommandPalette({ open, onClose }) {
  const nav = useNavigate();
  const { projects } = useProjects();
  const { isProductEnabled, isFeatureEnabled } = useEntitlements();
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState({ agents: [], knowledge: [], conversations: [], websites: [] });

  // Load searchable resources once the palette opens.
  useEffect(() => {
    if (!open) return undefined;
    let on = true;
    setLoading(true);
    (async () => {
      const calls = [
        api.get("/agents", { params: { limit: 100 } }),
        api.get("/knowledge-bases", { params: { limit: 100 } }),
        api.get("/conversations", { params: { limit: 50, sort: "recent" } }),
        api.get("/websites", { params: { limit: 100 } }),
      ];
      const [agents, knowledge, conversations, websites] = await Promise.allSettled(calls);
      if (!on) return;
      const val = (r) => (r.status === "fulfilled" ? r.value.data : null);
      setData({
        agents: normalize(val(agents), ["items", "agents"]),
        knowledge: normalize(val(knowledge), ["items", "knowledge_bases"]),
        conversations: normalize(val(conversations), ["items", "conversations"]),
        websites: normalize(val(websites), ["items", "websites"]),
      });
      setLoading(false);
    })();
    return () => {
      on = false;
    };
  }, [open]);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 30);
    }
  }, [open]);

  // Build grouped, filtered results.
  const groups = useMemo(() => {
    const term = q.trim().toLowerCase();
    const match = (s) => !term || String(s || "").toLowerCase().includes(term);

    const pages = PAGES
      .filter((p) => !p.product || isProductEnabled(p.product))
      .filter((p) => !p.feature || isFeatureEnabled(p.feature))
      .filter((p) => match(`${p.label} ${p.keywords}`)).map((p) => ({
      group: "pages",
      id: p.to,
      label: p.label,
      icon: p.icon,
      to: p.to,
    }));

    const proj = projects
      .filter((p) => match(p.name))
      .slice(0, 6)
      .map((p) => ({
        group: "projects",
        id: p.id,
        label: p.name,
        sub: `${p.resource_counts?.agents ?? 0} agents`,
        to: "/app/projects",
      }));

    const agents = data.agents
      .filter((a) => match(a.name))
      .slice(0, 6)
      .map((a) => ({ group: "agents", id: a.id, label: a.name || "Untitled agent", sub: a.type, to: `/app/agents/${a.id}` }));

    const knowledge = data.knowledge
      .filter((k) => match(k.name))
      .slice(0, 6)
      .map((k) => ({ group: "knowledge", id: k.id, label: k.name || "Knowledge base", to: `/app/knowledge-base/${k.id}` }));

    const conversations = data.conversations
      .filter((c) => match(c.title) || match(c.contact_name))
      .slice(0, 6)
      .map((c) => ({
        group: "conversations",
        id: c.id,
        label: c.title || c.contact_name || "Conversation",
        sub: c.contact_name && c.title ? c.contact_name : undefined,
        to: `/app/chat/${c.id}`,
      }));

    const websites = data.websites
      .filter((w) => match(w.name) || match(w.base_url))
      .slice(0, 6)
      .map((w) => ({ group: "websites", id: w.id, label: w.name || w.base_url, sub: w.base_url, to: "/app/websites" }));

    const ordered = [
      ["pages", pages],
      ["projects", proj],
      ["agents", agents],
      ["knowledge", knowledge],
      ["conversations", conversations],
      ["websites", websites],
    ].filter(([, arr]) => arr.length > 0);

    return ordered;
  }, [q, projects, data, isProductEnabled, isFeatureEnabled]);

  const flat = useMemo(() => groups.flatMap(([, arr]) => arr), [groups]);

  useEffect(() => {
    setActive(0);
  }, [q]);

  const choose = useCallback(
    (item) => {
      if (!item) return;
      onClose();
      nav(item.to);
    },
    [nav, onClose]
  );

  const onKeyDown = (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(flat.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      choose(flat[active]);
    }
  };

  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-idx="${active}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [active]);

  if (!open) return null;

  let runningIndex = -1;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center p-4 pt-[12vh]" data-testid="command-palette">
      <div className="absolute inset-0 bg-[#0F172A]/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-xl overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white shadow-2xl">
        <div className="flex items-center gap-3 border-b border-[#F1F5F9] px-4">
          <Search size={18} className="text-[#94A3B8]" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search projects, agents, knowledge, conversations…"
            className="flex-1 bg-transparent py-4 text-[15px] outline-none placeholder:text-[#94A3B8]"
            data-testid="command-palette-input"
          />
          {loading && <Loader2 size={16} className="animate-spin text-[#94A3B8]" />}
          <kbd className="hidden sm:block rounded-md border border-[#E2E8F0] bg-[#F8FAFC] px-1.5 py-0.5 text-[11px] text-[#94A3B8]">
            Esc
          </kbd>
        </div>

        <div ref={listRef} className="max-h-[55vh] overflow-y-auto p-2 scrollbar-thin">
          {flat.length === 0 ? (
            <div className="px-4 py-10 text-center text-sm text-[#94A3B8]">
              {loading ? "Searching…" : "No results found."}
            </div>
          ) : (
            groups.map(([key, arr]) => {
              const gm = GROUP_META[key];
              return (
                <div key={key} className="mb-1">
                  <p className="px-2.5 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8]">
                    {gm.label}
                  </p>
                  {arr.map((item) => {
                    runningIndex += 1;
                    const idx = runningIndex;
                    const Icon = item.icon || gm.icon;
                    const isActive = idx === active;
                    return (
                      <button
                        key={`${key}-${item.id}`}
                        data-idx={idx}
                        onMouseEnter={() => setActive(idx)}
                        onClick={() => choose(item)}
                        className={`flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left transition-colors ${
                          isActive ? "bg-[#EFF6FF]" : "hover:bg-[#F8FAFC]"
                        }`}
                      >
                        <span className="grid size-7 shrink-0 place-items-center rounded-lg bg-[#F1F5F9] text-[#475569]">
                          <Icon size={15} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[13.5px] font-medium text-[#0F172A]">{item.label}</span>
                          {item.sub && <span className="block truncate text-[11px] text-[#94A3B8]">{item.sub}</span>}
                        </span>
                        {isActive && <CornerDownLeft size={14} className="shrink-0 text-[#2563EB]" />}
                      </button>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
