import React, { useEffect, useRef, useState } from "react";
import { Activity, Cpu, MemoryStick, HardDrive, Users, Zap, Server } from "lucide-react";
import {
  PageHeader, StatCard, Glass, SectionTitle, Sparkline, Badge, LoadingState, ErrorState, useAdminTheme,
} from "@/components/admin/adminKit";
import { superAdminApi } from "@/lib/superAdmin";
import { formatApiError } from "@/lib/api";
import { fmtNum } from "@/components/admin/format";

const MAX = 30;

export default function AdminMonitoring() {
  const { t } = useAdminTheme();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [hist, setHist] = useState({ rps: [], chats: [], cpu: [], ram: [], online: [] });
  const timer = useRef(null);

  useEffect(() => {
    let alive = true;
    async function tick() {
      try {
        const d = await superAdminApi.overview();
        if (!alive) return;
        setData(d);
        setError("");
        setHist((h) => {
          const push = (arr, v) => [...arr, Number(v) || 0].slice(-MAX);
          return {
            rps: push(h.rps, d.live?.api_requests_per_sec),
            chats: push(h.chats, d.live?.concurrent_chats),
            cpu: push(h.cpu, d.system?.cpu),
            ram: push(h.ram, d.system?.ram),
            online: push(h.online, d.live?.online_users),
          };
        });
      } catch (e) {
        if (alive) setError(formatApiError(e?.response?.data?.detail) || "Failed to load live metrics.");
      }
    }
    tick();
    timer.current = setInterval(tick, 5000);
    return () => { alive = false; clearInterval(timer.current); };
  }, []);

  if (error && !data) return (
    <div><PageHeader icon={Activity} title="Live Monitoring" /><ErrorState message={error} onRetry={() => window.location.reload()} /></div>
  );
  if (!data) return <div><PageHeader icon={Activity} title="Live Monitoring" /><LoadingState label="Connecting to live metrics…" /></div>;

  const charts = [
    { label: "API requests / sec", data: hist.rps, color: t.brand, icon: Zap, value: data.live?.api_requests_per_sec },
    { label: "Concurrent chats", data: hist.chats, color: t.brand2, icon: Activity, value: data.live?.concurrent_chats },
    { label: "Online users", data: hist.online, color: "#16A34A", icon: Users, value: data.live?.online_users },
    { label: "CPU %", data: hist.cpu, color: "#D97706", icon: Cpu, value: data.system?.cpu },
    { label: "RAM %", data: hist.ram, color: "#06B6D4", icon: MemoryStick, value: data.system?.ram },
  ];

  return (
    <div>
      <PageHeader icon={Activity} title="Live Monitoring" subtitle="Real-time platform telemetry · refreshing every 5s"
        actions={<Badge tone="green">● live</Badge>} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="API req/sec" value={fmtNum(data.live?.api_requests_per_sec)} icon={Zap} tone="blue" />
        <StatCard label="Concurrent chats" value={fmtNum(data.live?.concurrent_chats)} icon={Activity} tone="purple" />
        <StatCard label="Concurrent calls" value={fmtNum(data.live?.concurrent_calls)} icon={Server} tone="indigo" />
        <StatCard label="Error rate" value={`${data.reliability?.error_rate ?? 0}%`} icon={HardDrive} tone={(data.reliability?.error_rate ?? 0) > 2 ? "red" : "green"} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {charts.map((c) => (
          <Glass key={c.label} className="p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="flex items-center gap-2 text-sm" style={{ color: t.sub }}><c.icon className="h-4 w-4" />{c.label}</span>
              <span className="font-semibold" style={{ color: t.ink }}>{c.value ?? "—"}</span>
            </div>
            <Sparkline data={c.data} width={360} height={56} color={c.color} />
          </Glass>
        ))}
      </div>
    </div>
  );
}
