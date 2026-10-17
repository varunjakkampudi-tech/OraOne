import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Inbox,
  Users,
  ChartNoAxesCombined,
  MessageSquare,
  Mic,
  Phone,
  Mail,
  Workflow,
  Lightbulb,
  Plug,
  CreditCard,
  Settings,
  CircleHelp,
  Bell,
  Search,
  Plus,
  ChevronDown,
  ChevronRight,
  Menu,
  X,
  PanelLeftClose,
  PanelLeftOpen,
  ArrowUpRight,
  Check,
  Boxes,
  Command,
  Globe,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { isWorkspaceDestinationActive, sampleWorkspaceName } from "@/lib/oraone";
import { WorkspaceContext } from "@/lib/workspace-context";
import logoUrl from "@/assets/oraone-logo-48.png";
import { StatusBadge } from "./status-badge";

export function Brand() {
  return (
    <span className="brand">
      <img
        className="brand-logo"
        src={logoUrl}
        width={32}
        height={32}
        alt="OraOne logo"
        decoding="async"
      />
      <strong>OraOne</strong>
    </span>
  );
}
const workspaceLinks = [
  { title: "Overview", to: "/app", icon: LayoutDashboard },
  { title: "Unified Inbox", to: "/app/inbox", icon: Inbox, badge: "5" },
  { title: "Customers & Leads", to: "/app/customers", icon: Users, badge: "5" },
  { title: "Analytics", to: "/app/analytics", icon: ChartNoAxesCombined },
] as const;
const productLinks = [{ title: "AI Chat", to: "/app/products/chat", icon: MessageSquare }] as const;
const managementLinks = [
  { title: "Integrations", to: "/app/integrations", icon: Plug },
  { title: "Team & Access", to: "/app/team", icon: Users },
  { title: "Free access & Usage", to: "/app/billing", icon: CreditCard },
  { title: "Workspace Settings", to: "/app/settings", icon: Settings },
] as const;
const chatLinks = [
  { title: "Overview", to: "/app/products/chat" },
  { title: "AI Assistants", to: "/app/products/chat/assistants", badge: "3" },
  { title: "Knowledge Base", to: "/app/products/chat/knowledge", badge: "142" },
  {
    title: "Website Widget",
    to: "/app/products/chat/assistants/$id/widget",
    params: { id: "support" },
  },
  { title: "Chat History", to: "/app/products/chat/conversations", badge: "5" },
] as const;

export function WorkspaceShell({ children }: { children: ReactNode }) {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(true);
  const [workspace, setWorkspace] = useState(sampleWorkspaceName);
  const [menu, setMenu] = useState<string | null>(null);
  const workspaceMenu = menu === "workspace";
  const createMenu = menu === "create";
  const profileMenu = menu === "profile";
  const setWorkspaceMenu = (open: boolean) => setMenu(open ? "workspace" : null);
  const setCreateMenu = (open: boolean) => setMenu(open ? "create" : null);
  const setProfileMenu = (open: boolean) => setMenu(open ? "profile" : null);
  useEffect(() => {
    const close = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenu(null);
    };
    const outside = (e: PointerEvent) => {
      if (!(e.target instanceof Element) || !e.target.closest(".menu-anchor")) setMenu(null);
    };
    document.addEventListener("keydown", close);
    document.addEventListener("pointerdown", outside);
    return () => {
      document.removeEventListener("keydown", close);
      document.removeEventListener("pointerdown", outside);
    };
  }, []);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const sample = workspace === sampleWorkspaceName;
  const workspaceValue = useMemo(() => ({ workspace, sample }), [workspace, sample]);
  useEffect(() => {
    setMobileOpen(false);
    setWorkspaceMenu(false);
    setCreateMenu(false);
    setProfileMenu(false);
  }, [path]);
  useEffect(() => {
    if (!mobileOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [mobileOpen]);
  const allLinks = [...workspaceLinks, ...productLinks, ...managementLinks];
  const active = (to: string) => isWorkspaceDestinationActive(path, to);
  const sidebar = (
    <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
      <div className="sidebar-heading">
        <span>WORKSPACE</span>
        <Button
          variant="ghost"
          size="icon"
          className="collapse-control"
          title={collapsed ? "Expand navigation" : "Collapse navigation"}
          aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="mobile-menu"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        >
          <X />
        </Button>
      </div>
      <nav aria-label="Main navigation">
        <div className="nav-section">
          {workspaceLinks.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              onClick={() => setMobileOpen(false)}
              activeOptions={{ exact: item.to === "/app" }}
              aria-current={active(item.to) ? "page" : undefined}
              className={`nav-item ${active(item.to) ? "active" : ""}`}
              title={item.title}
            >
              <item.icon />
              <span className="nav-label">{item.title}</span>
              {"badge" in item && sample && (
                <span className={`nav-badge ${item.to === "/app/inbox" ? "alert-badge" : ""}`}>
                  {item.badge}
                </span>
              )}
            </Link>
          ))}
        </div>
        <div className="nav-section">
          <p className="section-label">AI PRODUCTS</p>
          {productLinks.map((item) => (
            <div key={item.to}>
              <div className="product-nav-row">
                <Link
                  to={item.to}
                  title={item.title}
                  onClick={() => setMobileOpen(false)}
                  className={`nav-item product-${item.title.toLowerCase().replaceAll(" ", "-")} ${active(item.to) ? "active" : ""}`}
                >
                  <item.icon />
                  <span className="nav-label">{item.title}</span>
                </Link>
                {item.title === "AI Chat" && (
                  <Button
                    size="icon"
                    variant="ghost"
                    className="expand-chat"
                    title="Toggle AI Chat navigation"
                    aria-label="Toggle AI Chat navigation"
                    aria-expanded={chatOpen}
                    onClick={() => setChatOpen(!chatOpen)}
                  >
                    <ChevronDown className={chatOpen ? "rotate-180" : ""} />
                  </Button>
                )}
                {item.title !== "AI Chat" && (
                  <StatusBadge status="planned" className="planned-nav" />
                )}
              </div>
              {item.title === "AI Chat" && chatOpen && (
                <div className="chat-subnav">
                  {chatLinks.map((link) => (
                    <Link
                      key={link.to}
                      {...link}
                      onClick={() => setMobileOpen(false)}
                      className={`subnav-item ${path === link.to ? "selected" : ""}`}
                    >
                      <span>{link.title}</span>
                      {"badge" in link && sample && <small>{link.badge}</small>}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="nav-section">
          <p className="section-label">MANAGEMENT</p>
          {managementLinks.map((item) => (
            <Link
              to={item.to}
              key={item.to}
              onClick={() => setMobileOpen(false)}
              title={item.title}
              activeOptions={{ exact: false }}
              aria-current={active(item.to) ? "page" : undefined}
              className={`nav-item ${active(item.to) ? "active" : ""}`}
            >
              <item.icon />
              <span className="nav-label">{item.title}</span>
            </Link>
          ))}
        </div>
      </nav>
      <footer className="sidebar-footer">
        <Link to="/status" className="system-status">
          <span className="status-dot" />
          <span>Service status</span>
          <small>Preview</small>
        </Link>
        <Link to="/help" className="support-link">
          <CircleHelp />
          <span>Help & Support</span>
          <ArrowUpRight />
        </Link>
        <Link to="/app/products" className="support-link">
          <Boxes />
          <span>Explore all products</span>
          <ChevronRight />
        </Link>
      </footer>
    </aside>
  );
  return (
    <WorkspaceContext.Provider value={workspaceValue}>
      <div className={`workspace-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
        <header className="topbar">
          <Button
            variant="ghost"
            size="icon"
            className="mobile-menu"
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
          >
            <Menu />
          </Button>
          <Link to="/app" className="brand-link">
            <Brand />
          </Link>
          <div className="top-divider" />
          <div className="menu-anchor workspace-switcher">
            <Button
              variant="topbar"
              onClick={() => setWorkspaceMenu(!workspaceMenu)}
              aria-expanded={workspaceMenu}
            >
              <span className="workspace-letter">{sample ? "A" : "S"}</span>
              <span>{workspace}</span>
              <span className="production-tag">DEMO</span>
              <ChevronDown />
            </Button>
            {workspaceMenu && (
              <div className="floating-menu workspace-menu">
                <p className="menu-caption">YOUR WORKSPACES</p>
                {[sampleWorkspaceName, "Studio Workspace"].map((name) => (
                  <Button
                    key={name}
                    variant="ghost"
                    className="menu-item"
                    onClick={() => {
                      setWorkspace(name);
                      setWorkspaceMenu(false);
                    }}
                  >
                    <span className="workspace-letter">{name[0]}</span>
                    <span>{name}</span>
                    {name === workspace && <Check />}
                  </Button>
                ))}
                <div className="menu-rule" />
                <Button asChild variant="ghost" className="menu-item">
                  <Link to="/app/workspaces/new">
                    <Plus />
                    Create workspace
                  </Link>
                </Button>
              </div>
            )}
          </div>
          <Button
            variant="topbar"
            className="global-search"
            onClick={() => {
              setMenu(null);
              setSearchOpen(true);
            }}
          >
            <Search />
            <span>Search conversations, assistants, leads, workflows...</span>
            <kbd>⌘ K</kbd>
          </Button>
          <div className="top-actions">
            <div className="menu-anchor">
              <Button size="sm" onClick={() => setCreateMenu(!createMenu)}>
                <Plus />
                Create
                <ChevronDown />
              </Button>
              {createMenu && (
                <div className="floating-menu create-menu">
                  <Button asChild variant="ghost" className="menu-item">
                    <Link
                      to="/app/products/chat/assistants/new"
                      onClick={() => setCreateMenu(false)}
                    >
                      <MessageSquare />
                      New assistant
                    </Link>
                  </Button>
                  <Button asChild variant="ghost" className="menu-item">
                    <Link
                      to="/app/products/chat/knowledge/documents"
                      onClick={() => setCreateMenu(false)}
                    >
                      <Plus />
                      Add knowledge
                    </Link>
                  </Button>
                  <Button asChild variant="ghost" className="menu-item">
                    <Link to="/app/team/invitations" onClick={() => setCreateMenu(false)}>
                      <Users />
                      Invite teammate
                    </Link>
                  </Button>
                </div>
              )}
            </div>
            <Button
              asChild
              variant="topbar"
              size="icon"
              title="Help & Support"
              aria-label="Help and support"
              className="top-help"
            >
              <Link to="/help">
                <CircleHelp />
              </Link>
            </Button>
            <Button
              asChild
              variant="topbar"
              size="icon"
              title="Notifications"
              aria-label="Notifications, 4 unread"
              className="notification-control"
            >
              <Link to="/app/notifications">
                <Bell />
                <span className="notification-dot">4</span>
              </Link>
            </Button>
            <div className="menu-anchor">
              <Button
                variant="topbar"
                className="profile-control"
                onClick={() => setProfileMenu(!profileMenu)}
              >
                <span className="avatar avatar-primary">AM</span>
                <span className="profile-label">
                  <strong>Alex Mercer</strong>
                  <small>WORKSPACE DEMO</small>
                </span>
                <ChevronDown />
              </Button>
              {profileMenu && (
                <div className="floating-menu profile-menu">
                  <p className="menu-caption">ALEX MERCER · SAMPLE ACCOUNT</p>
                  <Button asChild variant="ghost" className="menu-item">
                    <Link to="/app/account/profile">
                      <Users />
                      My profile
                    </Link>
                  </Button>
                  <Button asChild variant="ghost" className="menu-item">
                    <Link to="/app/account/preferences">
                      <Settings />
                      Preferences
                    </Link>
                  </Button>
                  <Button asChild variant="ghost" className="menu-item">
                    <Link to="/auth/sign-in">
                      <ArrowUpRight />
                      Connect your account
                    </Link>
                  </Button>
                </div>
              )}
            </div>
          </div>
        </header>
        <Dialog open={mobileOpen} onOpenChange={setMobileOpen}>
          <DialogContent className="translate-x-0 translate-y-0 mobile-navigation-dialog workspace-navigation-dialog">
            <DialogTitle>Workspace navigation</DialogTitle>
            <DialogDescription className="sr-only">
              Open your workspace pages and products.
            </DialogDescription>
            {sidebar}
          </DialogContent>
        </Dialog>
        {sidebar}
        <a href="#workspace-content" className="skip-content">
          Skip to workspace content
        </a>
        <main id="workspace-content" className="workspace-main">
          {children}
        </main>
        <Dialog open={searchOpen} onOpenChange={setSearchOpen}>
          <DialogContent className="search-dialog">
            <DialogTitle>Search your workspace</DialogTitle>
            <DialogDescription>Find pages, products and shared workspace tools.</DialogDescription>
            <label className="search-field">
              <Search />
              <input
                autoFocus
                placeholder="What are you looking for?"
                aria-label="Search workspace pages"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <div className="search-results">
              {allLinks
                .filter((item) =>
                  (item.title + (item.to === "/app/billing" ? " billing usage" : ""))
                    .toLowerCase()
                    .includes(query.toLowerCase()),
                )
                .map((item) => (
                  <Button
                    variant="ghost"
                    key={item.to}
                    className="menu-item"
                    onClick={() => {
                      setSearchOpen(false);
                      navigate({ to: item.to });
                    }}
                  >
                    <item.icon />
                    {item.title}
                    <ArrowUpRight />
                  </Button>
                ))}
            </div>
            {allLinks.every(
              (item) =>
                !(item.title + (item.to === "/app/billing" ? " billing usage" : ""))
                  .toLowerCase()
                  .includes(query.toLowerCase()),
            ) && <p className="empty-copy">No matching pages.</p>}
          </DialogContent>
        </Dialog>
      </div>
    </WorkspaceContext.Provider>
  );
}
