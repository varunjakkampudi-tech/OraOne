import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  Users2,
  Share2,
  MessageSquare,
  CheckSquare,
  Bell,
  ListChecks,
  Loader2,
  ArrowRight,
  Activity as ActivityIcon,
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

const ACTION_LABELS = {
  team_created: "created a team",
  team_updated: "updated a team",
  shared: "shared a resource",
  commented: "left a comment",
  task_created: "created a task",
  task_updated: "updated a task",
};

const STAT_CARDS = [
  { key: "teams", label: "Teams", icon: Users2, tint: "bg-[#EEF2FF] text-[#4F46E5]", to: "/app/teams" },
  { key: "shared_resources", label: "Shared", icon: Share2, tint: "bg-[#ECFEFF] text-[#0891B2]", to: "/app/teams" },
  { key: "comments", label: "Comments", icon: MessageSquare, tint: "bg-[#F0FDF4] text-[#16A34A]", to: "/app/activity" },
  { key: "open_tasks", label: "Open Tasks", icon: CheckSquare, tint: "bg-[#FEF3C7] text-[#B45309]", to: "/app/tasks" },
  { key: "my_open_tasks", label: "My Tasks", icon: ListChecks, tint: "bg-[#FAE8FF] text-[#A21CAF]", to: "/app/tasks" },
  { key: "unread_notifications", label: "Unread", icon: Bell, tint: "bg-[#FEE2E2] text-[#DC2626]", to: "/app/notifications" },
];

export default function Workspace() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/collab/workspace");
      setOverview(data);
    } catch (e) {
      toast.error(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const totals = useMemo(() => overview?.totals || {}, [overview]);
  const activity = useMemo(() => overview?.recent_activity || [], [overview]);

  if (loading) {
    return (
      <div className="grid h-[60vh] place-items-center">
        <Loader2 className="h-6 w-6 animate-spin text-[#4F46E5]" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto max-w-6xl space-y-8 p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#EEF2FF] text-[#4F46E5]">
            <Users2 className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#0F172A]">Workspace</h1>
            <p className="text-sm text-[#64748B]">
              Collaborate across teams — shared resources, comments, tasks and activity in one place.
            </p>
          </div>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {STAT_CARDS.map((c) => (
          <Link
            key={c.key}
            to={c.to}
            className="group rounded-2xl border border-[#E2E8F0] bg-white p-4 transition hover:border-[#C7D2FE] hover:shadow-sm"
          >
            <div className={`grid h-9 w-9 place-items-center rounded-xl ${c.tint}`}>
              <c.icon className="h-4.5 w-4.5" />
            </div>
            <p className="mt-3 text-2xl font-bold tabular-nums text-[#0F172A]">{totals[c.key] ?? 0}</p>
            <p className="text-[12px] font-medium text-[#64748B]">{c.label}</p>
          </Link>
        ))}
      </div>

      {/* Recent activity */}
      <div className="rounded-2xl border border-[#E2E8F0] bg-white">
        <div className="flex items-center justify-between border-b border-[#E2E8F0] px-5 py-4">
          <div className="flex items-center gap-2">
            <ActivityIcon className="h-4.5 w-4.5 text-[#4F46E5]" />
            <h2 className="text-sm font-bold text-[#0F172A]">Recent activity</h2>
          </div>
          <Link
            to="/app/activity"
            className="inline-flex items-center gap-1 text-[12px] font-semibold text-[#4F46E5] hover:underline"
          >
            View all <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        {activity.length === 0 ? (
          <p className="px-5 py-10 text-center text-sm text-[#94A3B8]">
            No activity yet. Create a team or share a resource to get started.
          </p>
        ) : (
          <ul className="divide-y divide-[#F1F5F9]">
            {activity.map((ev) => (
              <li key={ev.id} className="flex items-start gap-3 px-5 py-3.5">
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#EEF2FF] text-[11px] font-bold text-[#4F46E5]">
                  {initials(ev.actor?.name) || "•"}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-[#0F172A]">
                    <span className="font-semibold">{ev.actor?.name || "Someone"}</span>{" "}
                    <span className="text-[#64748B]">{ACTION_LABELS[ev.action] || ev.action}</span>
                  </p>
                  <p className="truncate text-[12px] text-[#94A3B8]">{ev.summary}</p>
                </div>
                <span className="shrink-0 text-[11px] text-[#94A3B8]">{fmtRelative(ev.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </motion.div>
  );
}
