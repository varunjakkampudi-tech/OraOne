import { NavLink } from "react-router-dom";
import { ArrowUpRight, ShieldCheck, X } from "lucide-react";
import { useAdminTheme, GradientText } from "@/components/admin/adminKit";
import { ADMIN_NAV } from "@/components/admin/adminNav";

export default function AdminSidebar({ mobileOpen, onClose }) {
  const { t } = useAdminTheme();

  const body = (
    <div
      className="flex h-full flex-col"
      style={{
        background: t.sidebar,
        borderRight: `1px solid ${t.line}`,
      }}
    >
      <div
        className="flex items-center justify-between px-5 py-5"
        style={{ borderBottom: `1px solid ${t.line}` }}
      >
        <div className="flex items-center gap-2">
          <div
            className="grid h-8 w-8 place-items-center rounded-lg"
            style={{
              background: `linear-gradient(135deg,${t.brand},${t.brand2})`,
            }}
          >
            <ShieldCheck className="h-4.5 w-4.5 text-white" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold" style={{ color: "#F8FAFC" }}>
              <GradientText>OraOne</GradientText> Admin
            </div>
            <div
              className="text-[10px] uppercase tracking-wider"
              style={{ color: "#8492B2" }}
            >
              Control Center
            </div>
          </div>
        </div>
        <button
          className="lg:hidden"
          onClick={onClose}
          aria-label="Close menu"
          style={{ color: t.sub }}
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div
        className="px-5 pb-3 pt-5 text-[10px] font-semibold uppercase tracking-[0.18em]"
        style={{ color: "#8492B2" }}
      >
        Platform administration
      </div>
      <nav className="flex-1 overflow-y-auto px-3 pb-4 scrollbar-thin">
        {ADMIN_NAV.map((g) => (
          <div key={g.group} className="mb-4">
            <div
              className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider"
              style={{ color: "#8492B2" }}
            >
              {g.group}
            </div>
            <div className="space-y-0.5">
              {g.items.map((it) => (
                <NavLink
                  key={it.to}
                  to={it.to}
                  end={it.end}
                  onClick={onClose}
                  className="group flex items-center gap-2.5 rounded-lg px-2.5 py-2.5 text-sm transition"
                  style={({ isActive }) => ({
                    color: isActive ? "#fff" : t.sidebarInk,
                    background: isActive
                      ? "rgba(108,139,255,0.18)"
                      : "transparent",
                    boxShadow: isActive ? "inset 3px 0 0 #6C8BFF" : "none",
                    fontWeight: isActive ? 600 : 500,
                  })}
                >
                  <it.icon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{it.label}</span>
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div
        className="space-y-3 border-t px-4 py-4"
        style={{ borderColor: t.line }}
      >
        <NavLink
          to="/app"
          onClick={onClose}
          className="flex items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium transition"
          style={{
            background: "rgba(255,255,255,0.07)",
            color: "#F8FAFC",
            border: "1px solid rgba(255,255,255,0.1)",
          }}
        >
          <span>Customer workspace</span>
          <ArrowUpRight className="h-4 w-4" />
        </NavLink>
        <div className="px-1 text-[11px]" style={{ color: t.muted }}>
          Restricted access · Platform operators
        </div>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden w-[272px] shrink-0 lg:block">{body}</aside>
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={onClose} />
          <div className="absolute left-0 top-0 h-full w-72">{body}</div>
        </div>
      ) : null}
    </>
  );
}
