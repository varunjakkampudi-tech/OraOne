import React, { useEffect, useState, useCallback } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { Menu, Search, Sun, Moon, ShieldAlert, Loader2, LogOut, Command } from "lucide-react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AdminThemeProvider, useAdminTheme, Btn, GradientText } from "@/components/admin/adminKit";
import AdminSidebar from "@/components/admin/AdminSidebar";
import CommandPalette from "@/components/admin/CommandPalette";
import { superAdminApi } from "@/lib/superAdmin";

function TopBar({ onMenu, onSearch, admin }) {
  const { t, dark, toggle } = useAdminTheme();
  return (
    <header className="sticky top-0 z-30 flex items-center gap-3 px-4 py-3 sm:px-6"
      style={{ background: t.sidebar, backdropFilter: "blur(16px)", borderBottom: `1px solid ${t.line}` }}>
      <button className="lg:hidden" onClick={onMenu} aria-label="Open menu" style={{ color: t.sub }}><Menu className="h-5 w-5" /></button>
      <button onClick={onSearch}
        className="flex flex-1 items-center gap-2 rounded-xl px-3 py-2 text-sm sm:max-w-md"
        style={{ background: t.glassSolid, border: `1px solid ${t.line}`, color: t.sub }}>
        <Search className="h-4 w-4" />
        <span className="flex-1 text-left">Search customers, pages, agents…</span>
        <kbd className="hidden items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] sm:inline-flex" style={{ background: t.hover, color: t.muted }}>
          <Command className="h-3 w-3" />K
        </kbd>
      </button>
      <div className="ml-auto flex items-center gap-2">
        <button onClick={toggle} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"} className="grid h-9 w-9 place-items-center rounded-xl" style={{ background: t.glassSolid, border: `1px solid ${t.line}`, color: t.sub }}>
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
        <div className="hidden items-center gap-2 rounded-xl px-3 py-1.5 sm:flex" style={{ background: t.glassSolid, border: `1px solid ${t.line}` }}>
          <div className="grid h-6 w-6 place-items-center rounded-full text-[11px] font-semibold text-white" style={{ background: `linear-gradient(135deg,${t.brand},${t.brand2})` }}>
            {(admin?.email || "?").slice(0, 1).toUpperCase()}
          </div>
          <span className="max-w-[160px] truncate text-xs" style={{ color: t.ink }}>{admin?.email}</span>
        </div>
      </div>
    </header>
  );
}

function AccessDenied({ onExit }) {
  const { t } = useAdminTheme();
  return (
    <div className="grid min-h-screen place-items-center px-4" style={{ background: t.appBg }}>
      <div className="max-w-md rounded-2xl p-8 text-center" style={{ background: t.glass, border: `1px solid ${t.line}`, backdropFilter: "blur(14px)" }}>
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl" style={{ background: "rgba(220,38,38,0.12)" }}>
          <ShieldAlert className="h-7 w-7" style={{ color: "#DC2626" }} />
        </div>
        <h1 className="mt-4 text-xl font-semibold" style={{ color: t.ink }}>Restricted area</h1>
        <p className="mt-2 text-sm" style={{ color: t.sub }}>
          The <GradientText>OraOne</GradientText> Control Center is limited to platform administrators.
          Your account doesn’t have access.
        </p>
        <div className="mt-5 flex justify-center">
          <Btn onClick={onExit}><LogOut className="h-4 w-4" /> Back to app</Btn>
        </div>
      </div>
    </div>
  );
}

function Shell() {
  const { t } = useAdminTheme();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [state, setState] = useState("checking"); // checking | ok | denied
  const [admin, setAdmin] = useState(null);

  useEffect(() => { setMobileOpen(false); }, [pathname]);

  useEffect(() => {
    let alive = true;
    superAdminApi
      .me()
      .then((d) => { if (alive) { setAdmin(d); setState("ok"); } })
      .catch(() => { if (alive) setState("denied"); });
    return () => { alive = false; };
  }, []);

  const onKey = useCallback((e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      setPaletteOpen((o) => !o);
    }
  }, []);
  useEffect(() => {
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onKey]);

  if (state === "checking") {
    return (
      <div className="grid min-h-screen place-items-center" style={{ background: t.appBg, color: t.sub }}>
        <div className="flex items-center gap-2 text-sm"><Loader2 className="h-5 w-5 animate-spin" /> Verifying admin access…</div>
      </div>
    );
  }
  if (state === "denied") return <AccessDenied onExit={() => navigate("/app/dashboard")} />;

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: t.appBg }}>
      {/* Skip-to-content link for keyboard / screen-reader users */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[100] focus:px-4 focus:py-2 focus:rounded-lg focus:bg-[#2563EB] focus:text-white focus:font-semibold focus:shadow-lg focus:outline-none focus:ring-4 focus:ring-[#2563EB]/30"
      >
        Skip to main content
      </a>
      <AdminSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar onMenu={() => setMobileOpen(true)} onSearch={() => setPaletteOpen(true)} admin={admin} />
        <main id="main-content" tabIndex="-1" className="flex-1 overflow-y-auto scrollbar-thin outline-none">
          <div className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">
            <Outlet context={{ admin }} />
          </div>
        </main>
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}

export default function AdminLayout() {
  return (
    <ProtectedRoute>
      <AdminThemeProvider>
        <Shell />
      </AdminThemeProvider>
    </ProtectedRoute>
  );
}
