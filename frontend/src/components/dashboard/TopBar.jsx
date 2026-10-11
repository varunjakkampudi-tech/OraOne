import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, NavLink } from "react-router-dom";
import { Search, Plus, Menu } from "lucide-react";
import { DASH } from "@/constants/testIds";
import { useProjects } from "@/lib/projects";
import { useEntitlements } from "@/lib/entitlements";
import { resolveSection, filterByEntitlements } from "@/constants/navigation";
import ProfileMenu from "@/components/dashboard/ProfileMenu";
import HelpMenu from "@/components/dashboard/HelpMenu";
import NotificationsMenu from "@/components/dashboard/NotificationsMenu";
import CommandPalette from "@/components/dashboard/CommandPalette";

// Titles for standalone (non-sectioned) destinations. Section roots derive
// their title from `@/constants/navigation` so there's one source of truth.
const TITLES = {
  "/app/dashboard": "Dashboard",
  "/app/create-agent": "Create AI Agent",
  "/app/chat": "Chat",
  "/app/conversations": "Conversations",
  "/app/leads": "Leads",
  "/app/integrations": "Integrations",
  "/app/activity": "Activity & Notifications",
  "/app/notifications": "Notifications",
  "/app/portal": "Customer Portal",
  "/app/getting-started": "Getting Started",
  "/app/tickets": "Support Tickets",
  "/app/feature-requests": "Support Tickets",
  "/app/changelog": "Changelog",
  "/app/status": "Product Status",
};

// Pages whose data is scoped to the active project. We surface a project chip
// next to the title so it's always clear which project you're working in.
const PROJECT_SCOPED = new Set([
  "/app/dashboard",
  "/app/create-agent",
  "/app/agents",
  "/app/chat",
  "/app/conversations",
  "/app/leads",
  "/app/integrations",
  "/app/knowledge-base",
  "/app/activity",
]);

// The primary action adapts to the page you're on instead of always being
// "Create Agent". Navigates to the create surface (pages may also open their
// own modal via location state / the oraone:create event).
const CONTEXT_ACTIONS = {
  "/app/dashboard": { label: "New Project", to: "/app/projects", state: { openCreate: true } },
  "/app/projects": { label: "New Project", to: "/app/projects", state: { openCreate: true } },
  "/app/agents": { label: "Create Agent", to: "/app/agents/new" },
  "/app/knowledge-base": { label: "New Knowledge Base", to: "/app/knowledge-base", state: { create: true } },
  "/app/integrations": { label: "Connect App", to: "/app/integrations", state: { create: true } },
};
const DEFAULT_ACTION = { label: "Create Agent", to: "/app/create-agent" };

export default function TopBar({ onMenuClick = () => {} }) {
  const { pathname } = useLocation();
  const nav = useNavigate();
  const { activeProject } = useProjects();
  const { isProductEnabled, isFeatureEnabled } = useEntitlements();
  const [paletteOpen, setPaletteOpen] = useState(false);

  const section = resolveSection(pathname);
  const sectionTabs = section
    ? filterByEntitlements(section.tabs, { isProductEnabled, isFeatureEnabled })
    : [];

  const titleKey = Object.keys(TITLES).find((k) => pathname === k || pathname.startsWith(k + "/"));
  const title = section?.label || TITLES[titleKey] || "Dashboard";

  const scopeKey = section?.root || titleKey;
  const isProjectScoped = scopeKey ? PROJECT_SCOPED.has(scopeKey) : false;
  const action = CONTEXT_ACTIONS[section?.root] || CONTEXT_ACTIONS[titleKey] || DEFAULT_ACTION;

  // Cmd/Ctrl+K opens the global command palette.
  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(true);
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const runAction = () => {
    window.dispatchEvent(new CustomEvent("oraone:create", { detail: { key: section?.root || titleKey } }));
    nav(action.to, action.state ? { state: action.state } : undefined);
  };

  return (
    <div className="bg-white border-b border-[#E2E8F0]">
      <header className="h-16 flex items-center px-4 sm:px-6 gap-3">
      {/* Left: title */}
      <div className="flex items-center gap-3 min-w-0 shrink-0">
        <button
          onClick={onMenuClick}
          className="lg:hidden p-2 -ml-1 rounded-xl text-[#475569] hover:bg-[#F1F5F9]"
          aria-label="Open navigation menu"
          data-testid="dashboard-menu-btn"
        >
          <Menu size={20} />
        </button>
        {isProjectScoped && activeProject ? (
          <button
            onClick={() => nav("/app/projects")}
            className="text-lg sm:text-xl font-bold text-[#0F172A] tracking-tight truncate hover:text-[#2563EB] transition-colors"
            title={title}
            data-testid="topbar-workspace-name"
          >
            {title}
          </button>
        ) : (
          <h1 className="text-lg sm:text-xl font-bold text-[#0F172A] tracking-tight truncate">{title}</h1>
        )}
      </div>

      {/* Center: search */}
      <div className="flex flex-1 justify-center px-2">
        <button
          onClick={() => setPaletteOpen(true)}
          className="hidden md:flex items-center gap-2 px-4 py-2.5 rounded-full bg-[#F8FAFC] border border-[#E2E8F0] w-full max-w-lg text-left hover:bg-[#F1F5F9] transition-colors"
          data-testid="dashboard-search-input"
        >
          <Search size={16} className="text-[#64748B]" />
          <span className="text-sm flex-1 text-[#94A3B8] truncate">Search agents, conversations…</span>
          <kbd className="rounded-md border border-[#E2E8F0] bg-white px-1.5 py-0.5 text-[11px] text-[#94A3B8]">⌘K</kbd>
        </button>
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
        <button
          onClick={() => setPaletteOpen(true)}
          className="md:hidden p-2.5 rounded-full text-[#64748B] hover:bg-[#F1F5F9]"
          aria-label="Search"
          data-testid="dashboard-search-btn"
        >
          <Search size={18} />
        </button>

        <HelpMenu />

        <NotificationsMenu />

        <button
          onClick={runAction}
          className="inline-flex items-center gap-2 px-3 sm:px-4 py-2.5 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold transition-colors shrink-0 shadow-[0_8px_20px_-8px_rgba(37,99,235,0.6)]"
          aria-label={action.label}
          data-testid={DASH.createAgentBtn}
        >
          <Plus size={16} /> <span className="hidden sm:inline">{action.label}</span>
        </button>

        <div className="pl-1 ml-0.5 border-l border-[#E2E8F0]">
          <ProfileMenu />
        </div>
      </div>
      </header>

      {/* Section tab bar — turns a group of related pages into focused tabs. */}
      {sectionTabs.length > 1 && (
        <nav
          className="flex items-center gap-1 px-4 sm:px-6 overflow-x-auto scrollbar-thin"
          aria-label={`${title} sections`}
          data-testid="section-tabs"
        >
          {sectionTabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                `relative -mb-px whitespace-nowrap border-b-2 px-3 py-2.5 text-[13px] font-semibold transition-colors ${
                  isActive
                    ? "border-[#2563EB] text-[#2563EB]"
                    : "border-transparent text-[#64748B] hover:text-[#0F172A]"
                }`
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
      )}

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
