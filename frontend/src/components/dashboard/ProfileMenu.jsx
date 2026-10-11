import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Building2,
  FolderKanban,
  LifeBuoy,
  LogOut,
  ChevronDown,
  Settings,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useProjects } from "@/lib/projects";
import { superAdminApi } from "@/lib/superAdmin";

export default function ProfileMenu() {
  const { user, logout, organizationName, membershipRole } = useAuth();
  const { activeProject } = useProjects();
  const [open, setOpen] = useState(false);
  const [isPlatformAdmin, setIsPlatformAdmin] = useState(false);
  const ref = useRef(null);
  const nav = useNavigate();

  useEffect(() => {
    let alive = true;
    superAdminApi
      .me()
      .then(() => { if (alive) setIsPlatformAdmin(true); })
      .catch(() => { if (alive) setIsPlatformAdmin(false); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const go = (to) => {
    setOpen(false);
    nav(to);
  };

  const onLogout = async () => {
    setOpen(false);
    await logout();
    nav("/login");
  };

  const initial = (user?.full_name || "U").slice(0, 1).toUpperCase();

  return (
    <div className="relative" ref={ref} data-testid="profile-menu">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 rounded-xl p-1 pl-1.5 hover:bg-[#F1F5F9] transition-colors"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Open profile menu"
        data-testid="profile-menu-trigger"
      >
        <span className="size-8 rounded-full bg-gradient-to-br from-[#3B82F6] to-[#06B6D4] grid place-items-center text-white text-sm font-semibold">
          {initial}
        </span>
        <ChevronDown size={15} className="text-[#94A3B8]" />
      </button>

      {open && (
        <div
          className="absolute right-0 top-[calc(100%+0.5rem)] z-50 w-72 overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white shadow-xl"
          role="menu"
          data-testid="profile-menu-panel"
        >
          {/* Identity */}
          <div className="flex items-center gap-3 border-b border-[#F1F5F9] px-4 py-3">
            <span className="size-9 rounded-full bg-gradient-to-br from-[#3B82F6] to-[#06B6D4] grid place-items-center text-white text-sm font-semibold">
              {initial}
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-[#0F172A]">{user?.full_name || "User"}</p>
              <p className="truncate text-xs capitalize text-[#64748B]">{membershipRole || user?.role || "owner"}</p>
            </div>
          </div>

          {/* Context: workspace + project */}
          <div className="border-b border-[#F1F5F9] px-2 py-2">
            <div className="flex items-center gap-2.5 rounded-lg px-2.5 py-2">
              <Building2 size={15} className="text-[#94A3B8]" />
              <div className="min-w-0 flex-1">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8]">Workspace</p>
                <p className="truncate text-[13px] font-medium text-[#0F172A]">{organizationName || "Workspace"}</p>
              </div>
            </div>
            <button
              onClick={() => go("/app/projects")}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left hover:bg-[#F8FAFC]"
              role="menuitem"
            >
              <FolderKanban size={15} className="text-[#94A3B8]" />
              <div className="min-w-0 flex-1">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8]">Project</p>
                <p className="truncate text-[13px] font-medium text-[#0F172A]">{activeProject?.name || "First Project"}</p>
              </div>
              <span className="text-[11px] font-semibold text-[#2563EB]">Switch</span>
            </button>
            <button
              onClick={() => go("/app/team")}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left hover:bg-[#F8FAFC]"
              role="menuitem"
              data-testid="profile-team"
            >
              <Users size={15} className="text-[#94A3B8]" />
              <div className="min-w-0 flex-1">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-[#94A3B8]">Workspace</p>
                <p className="truncate text-[13px] font-medium text-[#0F172A]">Members &amp; roles</p>
              </div>
            </button>
          </div>

          {/* Footer */}
          <div className="border-t border-[#F1F5F9] px-2 py-2">
            <button
              onClick={() => go("/app/settings")}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium text-[#475569] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
              role="menuitem"
              data-testid="profile-settings"
            >
              <Settings size={15} className="text-[#94A3B8]" />
              Settings
            </button>
            {isPlatformAdmin && (
              <button
                onClick={() => go("/admin")}
                className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium text-[#475569] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
                role="menuitem"
                data-testid="profile-admin-panel"
              >
                <ShieldCheck size={15} className="text-[#94A3B8]" />
                Admin Panel
              </button>
            )}
            <button
              onClick={() => go("/app/tickets")}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium text-[#475569] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
              role="menuitem"
              data-testid="profile-support"
            >
              <LifeBuoy size={15} className="text-[#94A3B8]" />
              Support
            </button>
            <button
              onClick={onLogout}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] font-medium text-[#DC2626] hover:bg-red-50"
              role="menuitem"
              data-testid="profile-logout"
            >
              <LogOut size={15} />
              Log out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
