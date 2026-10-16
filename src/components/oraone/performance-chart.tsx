import { memo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

type TrendPoint = { day: string; conversations: number; resolved: number };

export default memo(function PerformanceChart({ data }: { data: TrendPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height="100%" debounce={80}>
      <AreaChart data={data} margin={{ left: 0, right: 14, top: 14, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="var(--border)" />
        <XAxis
          dataKey="day"
          tickLine={false}
          axisLine={false}
          tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
          dy={10}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
          width={45}
        />
        <Tooltip
          contentStyle={{
            background: "var(--card)",
            borderColor: "var(--border)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Area
          isAnimationActive={false}
          type="monotone"
          dataKey="conversations"
          stroke="var(--primary)"
          fill="var(--primary-soft)"
          strokeWidth={2.4}
        />
        <Area
          isAnimationActive={false}
          type="monotone"
          dataKey="resolved"
          stroke="var(--cyan)"
          fill="var(--cyan-soft)"
          strokeWidth={2.4}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
});
