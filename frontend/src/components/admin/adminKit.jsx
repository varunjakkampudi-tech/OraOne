import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  useEffect,
} from "react";
import {
  Loader2,
  AlertTriangle,
  Inbox,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";

/**
 * Self-contained design kit for the Super Admin Control Center.
 *
 * OraOne language: a calm operator workspace, a dark control rail, crisp
 * surfaces, blue/cyan accents, and a first-class dark mode. Theme is driven by an inline
 * palette (not tailwind's darkMode config) so it is fully portable.
 */

const LIGHT = {
  dark: false,
  appBg: "#F5F7FB",
  glass: "rgba(255,255,255,0.96)",
  glassSolid: "#FFFFFF",
  line: "#E2E8F0",
  ink: "#0F172A",
  sub: "#64748B",
  muted: "#94A3B8",
  brand: "#315CFF",
  brand2: "#16B8D4",
  sidebar: "#101A33",
  sidebarInk: "#B8C4DD",
  topbar: "rgba(255,255,255,0.92)",
  tableHead: "#F8FAFC",
  hover: "#F3F6FA",
  chipBg: "#EEF3FF",
  shadow: "0 12px 30px -18px rgba(15,23,42,0.35)",
};

const DARK = {
  dark: true,
  appBg:
    "radial-gradient(900px 500px at 90% -10%,rgba(22,184,212,0.12),transparent),#0A1020",
  glass: "rgba(16,26,48,0.88)",
  glassSolid: "#111A30",
  line: "#24314D",
  ink: "#E2E8F0",
  sub: "#94A3B8",
  muted: "#64748B",
  brand: "#6C8BFF",
  brand2: "#28C5DA",
  sidebar: "#0B1226",
  sidebarInk: "#C0CBE2",
  topbar: "rgba(15,23,42,0.94)",
  tableHead: "rgba(148,163,184,0.06)",
  hover: "rgba(148,163,184,0.10)",
  chipBg: "rgba(108,139,255,0.14)",
  shadow: "0 16px 40px -16px rgba(0,0,0,0.6)",
};

const ThemeCtx = createContext({ t: LIGHT, dark: false, toggle: () => {} });
export const useAdminTheme = () => useContext(ThemeCtx);

export function AdminThemeProvider({ children }) {
  const [dark, setDark] = useState(() => {
    try {
      return localStorage.getItem("oraone_admin_theme") === "dark";
    } catch {
      return false;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem("oraone_admin_theme", dark ? "dark" : "light");
    } catch {
      /* ignore */
    }
  }, [dark]);
  const toggle = useCallback(() => setDark((d) => !d), []);
  const t = dark ? DARK : LIGHT;
  const value = useMemo(() => ({ t, dark, toggle }), [t, dark, toggle]);
  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>;
}

export function GradientText({ children }) {
  const { t } = useAdminTheme();
  return (
    <span
      style={{
        background: `linear-gradient(90deg,${t.brand},${t.brand2})`,
        WebkitBackgroundClip: "text",
        WebkitTextFillColor: "transparent",
        backgroundClip: "text",
      }}
    >
      {children}
    </span>
  );
}

export function Glass({
  children,
  className = "",
  style = {},
  hover = false,
  onClick,
}) {
  const { t } = useAdminTheme();
  const [h, setH] = useState(false);
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setH(true)}
      onMouseLeave={() => setH(false)}
      className={`rounded-xl ${className}`}
      style={{
        background: t.glass,
        backdropFilter: "blur(10px)",
        WebkitBackdropFilter: "blur(10px)",
        border: `1px solid ${t.line}`,
        boxShadow: hover && h ? t.shadow : "none",
        transform: hover && h ? "translateY(-2px)" : "none",
        transition: "all .18s ease",
        cursor: onClick ? "pointer" : "default",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export function PageHeader({ title, subtitle, icon: Icon, actions }) {
  const { t } = useAdminTheme();
  return (
    <div className="mb-8 flex flex-wrap items-start justify-between gap-5">
      <div className="flex items-start gap-3">
        {Icon ? (
          <div
            className="grid h-10 w-10 place-items-center rounded-lg"
            style={{
              background: `linear-gradient(135deg,${t.brand},${t.brand2})`,
            }}
          >
            <Icon className="h-5 w-5 text-white" />
          </div>
        ) : null}
        <div>
          <div
            className="mb-1 text-[10px] font-semibold uppercase tracking-[0.16em]"
            style={{ color: t.muted }}
          >
            Platform administration
          </div>
          <h1
            className="text-[26px] font-semibold tracking-[-0.02em]"
            style={{ color: t.ink }}
          >
            {title}
          </h1>
          {subtitle ? (
            <p className="mt-0.5 text-sm" style={{ color: t.sub }}>
              {subtitle}
            </p>
          ) : null}
        </div>
      </div>
      {actions ? (
        <div className="flex items-center gap-2">{actions}</div>
      ) : null}
    </div>
  );
}

export function Badge({ children, tone = "slate" }) {
  const { dark } = useAdminTheme();
  const map = {
    slate: ["#64748B", dark ? "rgba(100,116,139,0.16)" : "#F1F5F9"],
    green: ["#16A34A", dark ? "rgba(22,163,74,0.16)" : "#ECFDF5"],
    blue: ["#2563EB", dark ? "rgba(37,99,235,0.16)" : "#EFF6FF"],
    indigo: ["#0EA5E9", dark ? "rgba(14,165,233,0.16)" : "#F0F9FF"],
    amber: ["#D97706", dark ? "rgba(217,119,6,0.16)" : "#FFFBEB"],
    red: ["#DC2626", dark ? "rgba(220,38,38,0.16)" : "#FEF2F2"],
    purple: ["#0891B2", dark ? "rgba(8,145,178,0.16)" : "#ECFEFF"],
  };
  const [fg, bg] = map[tone] || map.slate;
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={{ color: fg, background: bg }}
    >
      {children}
    </span>
  );
}

export function Btn({
  children,
  onClick,
  variant = "primary",
  size = "md",
  type = "button",
  disabled,
  className = "",
}) {
  const { t } = useAdminTheme();
  const pad = size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2 text-sm";
  const styles =
    variant === "primary"
      ? {
          background: `linear-gradient(135deg,${t.brand},${t.brand2})`,
          color: "#fff",
          border: "none",
        }
      : variant === "ghost"
        ? {
            background: "transparent",
            color: t.sub,
            border: `1px solid ${t.line}`,
          }
        : {
            background: t.glassSolid,
            color: t.ink,
            border: `1px solid ${t.line}`,
          };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center gap-1.5 rounded-lg font-medium transition disabled:opacity-50 ${pad} ${className}`}
      style={styles}
    >
      {children}
    </button>
  );
}

export function Delta({ value }) {
  if (value === null || value === undefined) return null;
  const up = value >= 0;
  return (
    <span
      className="inline-flex items-center gap-0.5 text-xs font-semibold"
      style={{ color: up ? "#16A34A" : "#DC2626" }}
    >
      {up ? (
        <ArrowUpRight className="h-3.5 w-3.5" />
      ) : (
        <ArrowDownRight className="h-3.5 w-3.5" />
      )}
      {Math.abs(value)}%
    </span>
  );
}

export function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  tone = "blue",
  delta,
}) {
  const { t } = useAdminTheme();
  const tones = {
    blue: t.brand,
    purple: t.brand2,
    green: "#16A34A",
    amber: "#D97706",
    red: "#DC2626",
    slate: t.sub,
  };
  const accent = tones[tone] || t.brand;
  return (
    <Glass className="p-4" hover>
      <div className="flex items-center justify-between">
        <span
          className="text-xs font-medium uppercase tracking-wide"
          style={{ color: t.sub }}
        >
          {label}
        </span>
        {Icon ? <Icon className="h-4 w-4" style={{ color: accent }} /> : null}
      </div>
      <div className="mt-2 flex items-end gap-2">
        <span
          className="text-2xl font-semibold tracking-tight"
          style={{ color: t.ink }}
        >
          {value}
        </span>
        <Delta value={delta} />
      </div>
      {sub ? (
        <p className="mt-1 text-xs" style={{ color: t.muted }}>
          {sub}
        </p>
      ) : null}
    </Glass>
  );
}

export function SectionTitle({ children, right }) {
  const { t } = useAdminTheme();
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2
        className="text-sm font-semibold uppercase tracking-wide"
        style={{ color: t.sub }}
      >
        {children}
      </h2>
      {right}
    </div>
  );
}

export function LoadingState({ label = "Loading…" }) {
  const { t } = useAdminTheme();
  return (
    <div
      className="flex items-center justify-center py-20"
      style={{ color: t.sub }}
    >
      <Loader2 className="mr-2 h-5 w-5 animate-spin" /> {label}
    </div>
  );
}

export function EmptyState({
  title = "Nothing here yet",
  hint,
  icon: Icon = Inbox,
}) {
  const { t } = useAdminTheme();
  return (
    <Glass className="flex flex-col items-center justify-center py-16 text-center">
      <div
        className="grid h-12 w-12 place-items-center rounded-xl"
        style={{ background: t.chipBg }}
      >
        <Icon className="h-6 w-6" style={{ color: t.brand }} />
      </div>
      <p className="mt-3 text-sm font-medium" style={{ color: t.ink }}>
        {title}
      </p>
      {hint ? (
        <p className="mt-1 max-w-sm text-xs" style={{ color: t.sub }}>
          {hint}
        </p>
      ) : null}
    </Glass>
  );
}

export function ErrorState({ message = "Something went wrong.", onRetry }) {
  const { t } = useAdminTheme();
  return (
    <Glass className="flex flex-col items-center justify-center py-16 text-center">
      <div
        className="grid h-12 w-12 place-items-center rounded-xl"
        style={{ background: "rgba(220,38,38,0.12)" }}
      >
        <AlertTriangle className="h-6 w-6" style={{ color: "#DC2626" }} />
      </div>
      <p className="mt-3 text-sm font-medium" style={{ color: t.ink }}>
        {message}
      </p>
      {onRetry ? (
        <div className="mt-3">
          <Btn variant="ghost" size="sm" onClick={onRetry}>
            Retry
          </Btn>
        </div>
      ) : null}
    </Glass>
  );
}

export function Toggle({ checked, onChange, disabled }) {
  const { t } = useAdminTheme();
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onChange?.(!checked)}
      className="relative inline-flex h-6 w-11 items-center rounded-full transition disabled:opacity-50"
      style={{
        background: checked
          ? `linear-gradient(135deg,${t.brand},${t.brand2})`
          : t.line,
      }}
    >
      <span
        className="inline-block h-5 w-5 transform rounded-full bg-white shadow transition"
        style={{ transform: checked ? "translateX(22px)" : "translateX(2px)" }}
      />
    </button>
  );
}

export function Sparkline({ data = [], width = 120, height = 36, color }) {
  const { t } = useAdminTheme();
  const stroke = color || t.brand;
  if (!data.length) return <svg width={width} height={height} />;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const span = max - min || 1;
  const pts = data
    .map(
      (v, i) =>
        `${(i / (data.length - 1 || 1)) * width},${height - ((v - min) / span) * height}`,
    )
    .join(" ");
  return (
    <svg width={width} height={height}>
      <polyline
        points={pts}
        fill="none"
        stroke={stroke}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Table({ columns, rows, onRowClick, empty, contained = false }) {
  const { t } = useAdminTheme();
  if (!rows || rows.length === 0) return empty || <EmptyState />;
  const table = (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr
            style={{
              borderBottom: `1px solid ${t.line}`,
              background: t.tableHead,
            }}
          >
            {columns.map((c) => (
              <th
                key={c.key}
                className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide"
                style={{ color: t.sub }}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row.id || i}
              onClick={() => onRowClick?.(row)}
              className="transition"
              style={{
                borderBottom:
                  i < rows.length - 1 ? `1px solid ${t.line}` : "none",
                cursor: onRowClick ? "pointer" : "default",
              }}
              onMouseEnter={(e) => {
                if (onRowClick) e.currentTarget.style.background = t.hover;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
              }}
            >
              {columns.map((c) => (
                <td
                  key={c.key}
                  className="px-4 py-3.5"
                  style={{ color: t.ink }}
                >
                  {c.render ? c.render(row) : (row[c.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  return contained ? table : <Glass className="overflow-hidden">{table}</Glass>;
}

export function SearchInput({ value, onChange, placeholder = "Search…" }) {
  const { t } = useAdminTheme();
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={placeholder}
      className="w-full rounded-lg px-3 py-2.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-[#315CFF]/40"
      style={{
        background: t.glassSolid,
        border: `1px solid ${t.line}`,
        color: t.ink,
      }}
    />
  );
}
