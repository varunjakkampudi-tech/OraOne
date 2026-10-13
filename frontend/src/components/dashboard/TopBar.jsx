import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, NavLink } from "react-router-dom";
import { ChevronDown, Search, Plus, Menu } from "lucide-react";
import { DASH } from "@/constants/testIds";
import { useEntitlements } from "@/lib/entitlements";
import { resolveSection, filterByEntitlements } from "@/constants/navigation";
import ProfileMenu from "@/components/dashboard/ProfileMenu";
import HelpMenu from "@/components/dashboard/HelpMenu";
import NotificationsMenu from "@/components/dashboard/NotificationsMenu";
import CommandPalette from "@/components/dashboard/CommandPalette";
import ProjectSwitcher from "@/components/dashboard/ProjectSwitcher";
import { BrandHeader } from "@/components/dashboard/Sidebar";
import { useAuth } from "@/lib/auth";

// Titles for standalone (non-sectioned) destinations. Section roots derive
// their title from `@/constants/navigation` so there's one source of truth.
const TITLES = {
  "/app/dashboard": "Dashboard",
  "/app/products": "Product portfolio",
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

// The primary action adapts to the page you're on instead of always being
// "Create Agent". Navigates to the create surface (pages may also open their
// own modal via location state / the oraone:create event).
const CONTEXT_ACTIONS = {
  "/app/dashboard": {
    label: "Create Agent",
    to: "/app/create-agent",
  },
  "/app/projects": {
    label: "New Project",
    to: "/app/projects",
    state: { openCreate: true },
  },
  "/app/agents": { label: "Create Agent", to: "/app/agents/new" },
  "/app/knowledge-base": {
    label: "New Knowledge Base",
    to: "/app/knowledge-base",
    state: { create: true },
  },
  "/app/integrations": {
    label: "Connect App",
    to: "/app/integrations",
    state: { create: true },
  },
};
const DEFAULT_ACTION = { label: "Create Agent", to: "/app/create-agent" };

export default function TopBar({ onMenuClick = () => {} }) {
  const { pathname, search } = useLocation();
  const nav = useNavigate();
  const { organizationName } = useAuth();
  const { isProductEnabled, isFeatureEnabled } = useEntitlements();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const createRef = useRef(null);

  const section = resolveSection(pathname, search);
  const sectionTabs = section
    ? filterByEntitlements(section.tabs, { isProductEnabled, isFeatureEnabled })
    : [];

  const titleKey = Object.keys(TITLES).find(
    (k) => pathname === k || pathname.startsWith(k + "/"),
  );
  const title = section?.label || TITLES[titleKey] || "Dashboard";

  const action =
    CONTEXT_ACTIONS[section?.root] ||
    CONTEXT_ACTIONS[titleKey] ||
    DEFAULT_ACTION;

  const isTabActive = (tab) => {
    const pathActive = tab.activePaths?.some((path) =>
      tab.end
        ? pathname === path
        : pathname === path || pathname.startsWith(`${path}/`),
    );
    const searchActive = tab.activeSearch ? tab.activeSearch(search) : true;
    return (
      (pathActive || (!tab.activePaths && pathname === tab.to)) && searchActive
    );
  };

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

  useEffect(() => {
    if (!createOpen) return undefined;
    const close = (event) => {
      if (createRef.current && !createRef.current.contains(event.target)) {
        setCreateOpen(false);
      }
    };
    const onKey = (event) => {
      if (event.key === "Escape") setCreateOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", onKey);
    };
  }, [createOpen]);

  return (
    <div className="topbar z-30 shrink-0 border-b border-[#26374D] bg-[#132238] text-white shadow-sm">
      <header className="flex h-16 items-center gap-3 px-4 sm:px-6">
        <div className="flex min-w-0 shrink-0 items-center gap-3">
          <button
            onClick={onMenuClick}
            className="-ml-1 rounded-xl p-2 text-slate-200 hover:bg-white/10 lg:hidden"
            aria-label="Open navigation menu"
            data-testid="dashboard-menu-btn"
          >
            <Menu size={20} />
          </button>
          <BrandHeader dark />
          <span
            className="hidden h-8 w-px bg-white/15 sm:block"
            aria-hidden="true"
          />
          <div
            className="hidden max-w-40 min-w-0 flex-col xl:flex"
            data-testid="topbar-workspace-name"
          >
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-300">
              Workspace
            </span>
            <span className="truncate text-sm font-semibold text-white">
              {organizationName || "Workspace"}
            </span>
          </div>
          <div className="hidden md:block">
            <ProjectSwitcher placement="header" />
          </div>
        </div>

        {/* Center: search */}
        <div className="flex flex-1 justify-center px-2">
          <button
            onClick={() => setPaletteOpen(true)}
            className="hidden w-full max-w-lg items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2.5 text-left text-slate-200 transition-colors hover:bg-white/10 md:flex"
            data-testid="dashboard-search-input"
          >
            <Search size={16} className="text-[#64748B]" />
            <span className="global-search flex-1 truncate text-[13px] text-slate-300">
              Search conversations, assistants, leads, workflows…
            </span>
            <kbd className="rounded-md border border-white/10 bg-black/10 px-1.5 py-0.5 text-[11px] text-slate-300">
              ⌘K
            </kbd>
          </button>
        </div>

        {/* Right: actions */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          <button
            onClick={() => setPaletteOpen(true)}
            className="rounded-full p-2.5 text-slate-200 hover:bg-white/10 md:hidden"
            aria-label="Search"
            data-testid="dashboard-search-btn"
          >
            <Search size={18} />
          </button>

          <div className="relative" ref={createRef}>
            <button
              onClick={() => setCreateOpen((open) => !open)}
              className="inline-flex shrink-0 items-center gap-2 rounded-full bg-[#2563EB] px-3 py-2.5 text-sm font-semibold text-white shadow-[0_8px_20px_-8px_rgba(37,99,235,0.6)] transition-colors hover:bg-[#1D4ED8] sm:px-4"
              aria-expanded={createOpen}
              aria-haspopup="menu"
              data-testid={DASH.createAgentBtn}
            >
              <Plus size={16} />
              <span className="hidden sm:inline">Create</span>
              <ChevronDown size={15} />
            </button>
            {createOpen && (
              <div
                className="absolute right-0 top-[calc(100%+0.5rem)] z-50 w-60 overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white p-1.5 shadow-xl"
                role="menu"
              >
                <button
                  type="button"
                  onClick={() => {
                    setCreateOpen(false);
                    nav(
                      action.to,
                      action.state ? { state: action.state } : undefined,
                    );
                  }}
                  className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-[#2563EB] hover:bg-[#EFF6FF]"
                  role="menuitem"
                >
                  <Plus size={16} /> {action.label}
                </button>
                <div className="my-1 border-t border-[#F1F5F9]" />
                <button
                  type="button"
                  onClick={() => {
                    setCreateOpen(false);
                    nav("/app/agents/new");
                  }}
                  className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-[13px] font-medium text-[#475569] hover:bg-[#F8FAFC]"
                  role="menuitem"
                >
                  <Plus size={15} /> New assistant
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setCreateOpen(false);
                    nav("/app/products/chat/knowledge/documents");
                  }}
                  className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-[13px] font-medium text-[#475569] hover:bg-[#F8FAFC]"
                  role="menuitem"
                >
                  <Plus size={15} /> Add knowledge
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setCreateOpen(false);
                    nav("/app/team/invitations");
                  }}
                  className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-[13px] font-medium text-[#475569] hover:bg-[#F8FAFC]"
                  role="menuitem"
                >
                  <Plus size={15} /> Invite teammate
                </button>
              </div>
            )}
          </div>
          <div className="hidden sm:block">
            <HelpMenu dark />
          </div>

          <NotificationsMenu dark />

          <div className="ml-0.5 border-l border-white/15 pl-1">
            <ProfileMenu dark />
          </div>
        </div>
      </header>

      {/* Section tab bar — turns a group of related pages into focused tabs. */}
      {sectionTabs.length > 1 && (
        <nav
          className="flex items-center gap-1 overflow-x-auto border-t border-white/10 bg-white px-4 text-slate-600 scrollbar-thin sm:px-6"
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
                  isActive || isTabActive(tab)
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

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
      />
    </div>
  );
}
