import React from "react";
import { NavLink, Link } from "react-router-dom";
import { X } from "lucide-react";
import { Logo } from "@/components/marketing/Logo";
import { useAuth } from "@/lib/auth";
import { useBranding } from "@/hooks/useBranding";
import { useEntitlements } from "@/lib/entitlements";
import ProjectSwitcher from "@/components/dashboard/ProjectSwitcher";
import {
  NAV_GROUPS,
  filterByEntitlements,
} from "@/constants/navigation";

// ─────────────────────────────────────────────────────────────────────────────
// Minimal, product-first navigation. The sidebar lists only the top-level
// destinations; everything else (versions, coverage, billing, API keys, audit
// logs…) is grouped into a section's tab bar or into Settings. CRM and
// future products appear automatically when the org is entitled — driven by the
// shared `@/constants/navigation` config, never hard-coded here.
// ─────────────────────────────────────────────────────────────────────────────

function BrandHeader() {
  const { branding } = useBranding();
  const { organizationName } = useAuth();
  const workspace = organizationName || branding?.organization_name || "Workspace";

  const mark = branding?.logo_url ? (
    <img
      src={branding.logo_url}
      alt={branding.brand_name || workspace || "Brand"}
      className="h-7 max-w-[150px] object-contain"
      data-testid="sidebar-brand-logo"
    />
  ) : (
    <Logo />
  );

  return (
    <Link
      to="/app/dashboard"
      className="min-w-0 block rounded-lg -m-1 p-1 transition-colors hover:bg-[#F8FAFC]"
      aria-label="Go to dashboard"
      data-testid="sidebar-brand-home"
    >
      {mark}
    </Link>
  );
}

const linkClass = ({ isActive }) =>
  `flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
    isActive
      ? "bg-[#F0F6FF] text-[#2563EB]"
      : "text-[#475569] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
  }`;

function NavItem({ item, onItemClick }) {
  const Icon = item.icon;

  // Temporarily disabled destinations stay visible for discovery
  // but are not navigable. Rendered as a muted, non-interactive row.
  if (item.disabled) {
    return (
      <div
        className="flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium text-[#94A3B8] cursor-not-allowed select-none"
        data-testid={item.id}
        aria-disabled="true"
        title="Coming soon"
      >
        <Icon size={18} />
        <span className="flex-1">{item.label}</span>
        {item.badge && (
          <span className="rounded-full bg-[#F1F5F9] px-2 py-0.5 text-[10px] font-bold text-[#94A3B8]">
            {item.badge}
          </span>
        )}
      </div>
    );
  }

  return (
    <NavLink
      to={item.to}
      data-testid={item.id}
      data-tour={item.tour}
      onClick={onItemClick}
      end={item.end}
      className={linkClass}
    >
      <Icon size={18} />
      <span className="flex-1">{item.label}</span>
      {item.badge && (
        <span className="rounded-full bg-[#DBEAFE] px-2 py-0.5 text-[10px] font-bold text-[#2563EB]">
          {item.badge}
        </span>
      )}
    </NavLink>
  );
}

function SidebarContent({ onItemClick, showClose, onClose }) {
  const { isProductEnabled, isFeatureEnabled } = useEntitlements();

  const groups = NAV_GROUPS
    .map((g) => ({ ...g, items: filterByEntitlements(g.items, { isProductEnabled, isFeatureEnabled }) }))
    .filter((g) => g.items.length > 0);

  return (
    <>
      <div className="h-16 px-5 flex items-center justify-between border-b border-[#E2E8F0]">
        <BrandHeader />
        {showClose && (
          <button
            onClick={onClose}
            className="lg:hidden p-2 rounded-lg text-[#64748B] hover:bg-[#F1F5F9]"
            aria-label="Close menu"
            data-testid="sidebar-close-btn"
          >
            <X size={18} />
          </button>
        )}
      </div>

      <ProjectSwitcher onNavigate={onItemClick} />

      <nav className="flex-1 overflow-y-auto p-3 space-y-1 scrollbar-thin">
        {groups.map((group, gi) => (
          <div key={group.label || `g-${gi}`} className={gi > 0 ? "pt-1.5" : ""}>
            {group.label && (
              <p className="px-3 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-[0.09em] text-[#94A3B8]">
                {group.label}
              </p>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <NavItem key={item.to} item={item} onItemClick={onItemClick} />
              ))}
            </div>
          </div>
        ))}
      </nav>
    </>
  );
}

export default function Sidebar({ mobileOpen = false, onClose = () => {} }) {
  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-64 bg-white border-r border-[#E2E8F0] flex-shrink-0 flex-col">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      <div
        className={`lg:hidden fixed inset-0 z-50 ${mobileOpen ? "" : "pointer-events-none"}`}
        aria-hidden={!mobileOpen}
      >
        {/* Backdrop */}
        <div
          onClick={onClose}
          className={`absolute inset-0 bg-[#0F172A]/50 backdrop-blur-sm transition-opacity duration-300 ${
            mobileOpen ? "opacity-100" : "opacity-0"
          }`}
          data-testid="sidebar-backdrop"
        />
        {/* Drawer */}
        <aside
          className={`absolute left-0 top-0 h-full w-72 max-w-[85%] bg-white border-r border-[#E2E8F0] flex flex-col shadow-2xl transition-transform duration-300 ${
            mobileOpen ? "translate-x-0" : "-translate-x-full"
          }`}
          role="dialog"
          aria-modal="true"
          aria-label="Navigation menu"
          data-testid="mobile-sidebar"
        >
          <SidebarContent
            onItemClick={onClose}
            showClose
            onClose={onClose}
          />
        </aside>
      </div>
    </>
  );
}
