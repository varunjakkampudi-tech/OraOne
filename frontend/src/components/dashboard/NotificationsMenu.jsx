import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  CheckCheck,
  Loader2,
  Bot,
  BookOpen,
  Globe,
  Plug,
  MessagesSquare,
  Users,
  Workflow,
  CreditCard,
  Gauge,
  AlertTriangle,
  CheckCircle2,
  ArrowUpRight,
} from "lucide-react";
import { api } from "@/lib/api";

function fmtRelative(value) {
  if (!value) return "";
  const then = new Date(value).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Date.now() - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

// Map a notification to an icon + the place it should open. Every notification
// is actionable — clicking it navigates the user straight to the resource.
const TYPE_META = {
  agent_created: { icon: Bot, tint: "bg-[#EFF6FF] text-[#2563EB]", to: () => "/app/agents" },
  agent_deployed: { icon: Bot, tint: "bg-[#EFF6FF] text-[#2563EB]", to: () => "/app/agents" },
  knowledge_indexed: { icon: BookOpen, tint: "bg-[#DCFCE7] text-[#16A34A]", to: () => "/app/knowledge-base" },
  knowledge_sync: { icon: BookOpen, tint: "bg-[#DCFCE7] text-[#16A34A]", to: () => "/app/knowledge-base" },
  website_crawled: { icon: Globe, tint: "bg-[#EFF6FF] text-[#2563EB]", to: () => "/app/websites" },
  website_failed: { icon: AlertTriangle, tint: "bg-[#FEE2E2] text-[#DC2626]", to: () => "/app/websites" },
  crawl_failed: { icon: AlertTriangle, tint: "bg-[#FEE2E2] text-[#DC2626]", to: () => "/app/websites" },
  integration_expired: { icon: Plug, tint: "bg-[#FEF3C7] text-[#B45309]", to: () => "/app/integrations" },
  integration_disconnected: { icon: Plug, tint: "bg-[#FEE2E2] text-[#DC2626]", to: () => "/app/integrations" },
  conversation: { icon: MessagesSquare, tint: "bg-[#DCFCE7] text-[#16A34A]", to: (n) => (n.resource_id ? `/app/chat/${n.resource_id}` : "/app/conversations") },
  new_conversation: { icon: MessagesSquare, tint: "bg-[#DCFCE7] text-[#16A34A]", to: (n) => (n.resource_id ? `/app/chat/${n.resource_id}` : "/app/conversations") },
  lead: { icon: Users, tint: "bg-[#E0F2FE] text-[#0EA5E9]", to: () => "/app/leads" },
  new_lead: { icon: Users, tint: "bg-[#E0F2FE] text-[#0EA5E9]", to: () => "/app/leads" },
  workflow_failed: { icon: Workflow, tint: "bg-[#FEE2E2] text-[#DC2626]", to: () => "/app/workflows" },
  workflow_completed: { icon: Workflow, tint: "bg-[#DCFCE7] text-[#16A34A]", to: () => "/app/workflows" },
  team_invite: { icon: Users, tint: "bg-[#EFF6FF] text-[#2563EB]", to: () => "/app/team" },
  member_joined: { icon: Users, tint: "bg-[#EFF6FF] text-[#2563EB]", to: () => "/app/team" },
  payment_failed: { icon: CreditCard, tint: "bg-[#FEE2E2] text-[#DC2626]", to: () => "/app/billing" },
  usage_limit: { icon: Gauge, tint: "bg-[#FEF3C7] text-[#B45309]", to: () => "/app/usage" },
};

function metaFor(n) {
  return (
    TYPE_META[n.type] || {
      icon: n.read ? CheckCircle2 : Bell,
      tint: "bg-[#F1F5F9] text-[#475569]",
      to: () => "/app/activity",
    }
  );
}

export default function NotificationsMenu() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);
  const nav = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/notifications", { params: { limit: 8 } });
      setItems(Array.isArray(data?.notifications) ? data.notifications : []);
      setUnread(data?.unread_count || 0);
    } catch {
      setItems([]);
      setUnread(0);
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll the unread count quietly so the badge stays fresh.
  useEffect(() => {
    let on = true;
    const ping = async () => {
      try {
        const { data } = await api.get("/notifications", { params: { limit: 1 } });
        if (on) setUnread(data?.unread_count || 0);
      } catch {
        /* ignore */
      }
    };
    ping();
    const t = setInterval(ping, 60000);
    return () => {
      on = false;
      clearInterval(t);
    };
  }, []);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  useEffect(() => {
    if (!open) return undefined;
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const markAll = async () => {
    try {
      await api.post("/notifications/read-all");
      setItems((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnread(0);
    } catch {
      /* ignore */
    }
  };

  const openItem = async (n) => {
    const meta = metaFor(n);
    const dest = n.link || n.url || meta.to(n);
    if (!n.read) {
      api.put(`/notifications/${n.id}/read`).catch(() => {});
      setUnread((u) => Math.max(0, u - 1));
    }
    setOpen(false);
    nav(dest);
  };

  return (
    <div className="relative" ref={ref} data-testid="notifications-menu">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative p-2.5 rounded-xl text-[#64748B] hover:bg-[#F1F5F9]"
        aria-label="Notifications"
        aria-haspopup="menu"
        aria-expanded={open}
        data-testid="dashboard-notifications-btn"
      >
        <Bell size={18} />
        {unread > 0 && (
          <span
            className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-[#EF4444] text-[10px] font-bold text-white grid place-items-center"
            data-testid="notifications-badge"
          >
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 top-[calc(100%+0.5rem)] z-50 w-[360px] overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white shadow-xl"
          role="menu"
          data-testid="notifications-panel"
        >
          <div className="flex items-center justify-between border-b border-[#F1F5F9] px-4 py-3">
            <span className="text-sm font-semibold text-[#0F172A]">Notifications</span>
            {unread > 0 && (
              <button
                onClick={markAll}
                className="inline-flex items-center gap-1.5 text-[12px] font-semibold text-[#2563EB] hover:underline"
              >
                <CheckCheck size={14} /> Mark all read
              </button>
            )}
          </div>

          <div className="max-h-[360px] overflow-y-auto scrollbar-thin">
            {loading ? (
              <div className="grid place-items-center py-12">
                <Loader2 className="h-5 w-5 animate-spin text-[#2563EB]" />
              </div>
            ) : items.length === 0 ? (
              <div className="px-4 py-12 text-center">
                <CheckCircle2 className="mx-auto mb-2 h-7 w-7 text-[#CBD5E1]" />
                <p className="text-sm text-[#64748B]">You&apos;re all caught up.</p>
              </div>
            ) : (
              <ul className="divide-y divide-[#F1F5F9]">
                {items.map((n) => {
                  const meta = metaFor(n);
                  const Icon = meta.icon;
                  return (
                    <li key={n.id}>
                      <button
                        onClick={() => openItem(n)}
                        className={`group flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-[#F8FAFC] ${
                          n.read ? "" : "bg-[#F8FAFF]"
                        }`}
                      >
                        <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${meta.tint}`}>
                          <Icon className="h-4 w-4" />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="flex items-center gap-1.5 text-[13px] font-semibold text-[#0F172A]">
                            {!n.read && <span className="size-1.5 rounded-full bg-[#2563EB]" />}
                            <span className="truncate">{n.title}</span>
                          </p>
                          {n.body && <p className="mt-0.5 line-clamp-2 text-[12px] text-[#64748B]">{n.body}</p>}
                          <p className="mt-0.5 text-[11px] text-[#94A3B8]">{fmtRelative(n.created_at)}</p>
                        </div>
                        <ArrowUpRight
                          size={14}
                          className="mt-1 shrink-0 text-[#CBD5E1] transition-colors group-hover:text-[#2563EB]"
                        />
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          <button
            onClick={() => {
              setOpen(false);
              nav("/app/activity");
            }}
            className="block w-full border-t border-[#F1F5F9] px-4 py-3 text-center text-[13px] font-semibold text-[#2563EB] hover:bg-[#F8FAFC]"
          >
            View all activity
          </button>
        </div>
      )}
    </div>
  );
}
