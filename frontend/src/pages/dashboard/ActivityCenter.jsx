import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity as ActivityIcon,
  Bell,
  Loader2,
  CheckCheck,
  Share2,
  MessageSquare,
  Users2,
  CheckSquare,
  AtSign,
  Dot,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";

function fmtRelative(value) {
  if (!value) return "—";
  const then = new Date(value).getTime();
  const diff = Date.now() - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function initials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

const ACTION_META = {
  team_created: { icon: Users2, tint: "bg-[#EFF6FF] text-[#2563EB]" },
  team_updated: { icon: Users2, tint: "bg-[#EFF6FF] text-[#2563EB]" },
  shared: { icon: Share2, tint: "bg-[#ECFEFF] text-[#0891B2]" },
  commented: { icon: MessageSquare, tint: "bg-[#F0FDF4] text-[#16A34A]" },
  task_created: { icon: CheckSquare, tint: "bg-[#FEF3C7] text-[#B45309]" },
  task_updated: { icon: CheckSquare, tint: "bg-[#FEF3C7] text-[#B45309]" },
};

const NOTIF_META = {
  mention: { icon: AtSign, tint: "bg-[#FAE8FF] text-[#A21CAF]" },
  comment: { icon: MessageSquare, tint: "bg-[#F0FDF4] text-[#16A34A]" },
  share: { icon: Share2, tint: "bg-[#ECFEFF] text-[#0891B2]" },
  task_assigned: { icon: CheckSquare, tint: "bg-[#FEF3C7] text-[#B45309]" },
  team_invite: { icon: Users2, tint: "bg-[#EFF6FF] text-[#2563EB]" },
};

function ActivityList() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let on = true;
    setLoading(true);
    api
      .get("/activity", { params: { limit: 100 } })
      .then(({ data }) => on && setItems(Array.isArray(data?.activity) ? data.activity : []))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => on && setLoading(false));
    return () => {
      on = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="grid place-items-center py-16">
        <Loader2 className="h-5 w-5 animate-spin text-[#2563EB]" />
      </div>
    );
  }
  if (!items.length) {
    return <p className="py-16 text-center text-sm text-[#94A3B8]">No activity yet.</p>;
  }
  return (
    <ul className="divide-y divide-[#F1F5F9]">
      {items.map((ev) => {
        const meta = ACTION_META[ev.action] || { icon: ActivityIcon, tint: "bg-[#F1F5F9] text-[#475569]" };
        const Icon = meta.icon;
        return (
          <li key={ev.id} className="flex items-start gap-3 px-5 py-3.5">
            <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${meta.tint}`}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-[#0F172A]">
                <span className="font-semibold">{ev.actor?.name || "Someone"}</span>{" "}
                <span className="text-[#64748B]">{ev.summary}</span>
              </p>
              {ev.resource_type && (
                <p className="mt-0.5 text-[11px] text-[#94A3B8]">
                  {ev.resource_type}
                  {ev.resource_id ? ` · ${ev.resource_id}` : ""}
                </p>
              )}
            </div>
            <span className="shrink-0 text-[11px] text-[#94A3B8]">{fmtRelative(ev.created_at)}</span>
          </li>
        );
      })}
    </ul>
  );
}

function NotificationsList() {
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/notifications", { params: { limit: 100 } });
      setItems(Array.isArray(data?.notifications) ? data.notifications : []);
      setUnread(data?.unread_count || 0);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const markRead = async (id) => {
    try {
      await api.put(`/notifications/${id}/read`);
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
      setUnread((u) => Math.max(0, u - 1));
    } catch (e) {
      toast.error(formatApiError(e));
    }
  };

  const markAll = async () => {
    setBusy(true);
    try {
      await api.post("/notifications/read-all");
      setItems((prev) => prev.map((n) => ({ ...n, read: true })));
      setUnread(0);
      toast.success("All notifications marked read");
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setBusy(false);
    }
  };
  if (loading) {
    return (
      <div className="grid place-items-center py-16">
        <Loader2 className="h-5 w-5 animate-spin text-[#2563EB]" />
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center justify-between border-b border-[#E2E8F0] px-5 py-3">
        <span className="text-[12px] font-semibold text-[#64748B]">
          {unread > 0 ? `${unread} unread` : "All caught up"}
        </span>
        {unread > 0 && (
          <button
            onClick={markAll}
            disabled={busy}
            className="inline-flex items-center gap-1.5 text-[12px] font-semibold text-[#2563EB] hover:underline disabled:opacity-50"
          >
            <CheckCheck className="h-3.5 w-3.5" /> Mark all read
          </button>
        )}
      </div>
      {!items.length ? (
        <p className="py-16 text-center text-sm text-[#94A3B8]">No notifications yet.</p>
      ) : (
        <ul className="divide-y divide-[#F1F5F9]">
          {items.map((n) => {
            const meta = NOTIF_META[n.type] || { icon: Bell, tint: "bg-[#F1F5F9] text-[#475569]" };
            const Icon = meta.icon;
            return (
              <li
                key={n.id}
                className={`flex items-start gap-3 px-5 py-3.5 ${n.read ? "" : "bg-[#F8FAFF]"}`}
              >
                <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${meta.tint}`}>
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-1 text-sm font-semibold text-[#0F172A]">
                    {!n.read && <Dot className="-ml-2 h-5 w-5 text-[#2563EB]" />}
                    {n.title}
                  </p>
                  {n.body && <p className="mt-0.5 text-[12px] text-[#64748B]">{n.body}</p>}
                  <p className="mt-0.5 text-[11px] text-[#94A3B8]">{fmtRelative(n.created_at)}</p>
                </div>
                {!n.read && (
                  <button
                    onClick={() => markRead(n.id)}
                    className="shrink-0 rounded-lg px-2 py-1 text-[11px] font-semibold text-[#2563EB] hover:bg-[#EFF6FF]"
                  >
                    Mark read
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}

export default function ActivityCenter({ defaultTab = "activity" }) {
  const [tab, setTab] = useState(defaultTab);

  const tabs = useMemo(
    () => [
      { key: "activity", label: "Activity", icon: ActivityIcon },
      { key: "notifications", label: "Notifications", icon: Bell },
    ],
    []
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-3xl space-y-6 p-6"
    >
      <div className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#EFF6FF] text-[#2563EB]">
          <ActivityIcon className="h-6 w-6" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#0F172A]">Activity & Notifications</h1>
          <p className="text-sm text-[#64748B]">Stay on top of what's happening across your workspace.</p>
        </div>
      </div>

      <div className="inline-flex rounded-xl border border-[#E2E8F0] bg-white p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition ${
              tab === t.key ? "bg-[#2563EB] text-white" : "text-[#475569] hover:bg-[#F8FAFC]"
            }`}
          >
            <t.icon className="h-4 w-4" /> {t.label}
          </button>
        ))}
      </div>

      <div className="rounded-2xl border border-[#E2E8F0] bg-white">
        {tab === "activity" ? <ActivityList /> : <NotificationsList />}
      </div>
    </motion.div>
  );
}
