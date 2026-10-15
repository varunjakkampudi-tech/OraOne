import { useEffect, useRef, useState } from "react";
import { NavLink, Link, useLocation } from "react-router-dom";
import { ChevronDown, X } from "lucide-react";
import { Logo, OraMark } from "@/components/marketing/Logo";
import { useAuth } from "@/lib/auth";
import { useBranding } from "@/hooks/useBranding";
import { useEntitlements } from "@/lib/entitlements";
import ProjectSwitcher from "@/components/dashboard/ProjectSwitcher";
import { NAV_GROUPS, filterByEntitlements } from "@/constants/navigation";

// ─────────────────────────────────────────────────────────────────────────────
// Minimal, product-first navigation. The sidebar lists only the top-level
// destinations; everything else (versions, coverage, billing, API keys, audit
// logs…) is grouped into a section's tab bar or into Settings. CRM and
// future products appear automatically when the org is entitled — driven by the
// shared `@/constants/navigation` config, never hard-coded here.
// ─────────────────────────────────────────────────────────────────────────────

export function BrandHeader({ dark = false }) {
  const { branding } = useBranding();
  const { organizationName } = useAuth();
  const workspace =
    organizationName || branding?.organization_name || "Workspace";

  const mark = branding?.logo_url ? (
    <>
      <img
        src={branding.logo_url}
        alt={branding.brand_name || workspace || "Brand"}
        className="hidden h-7 max-w-[150px] object-contain sm:block"
        data-testid="sidebar-brand-logo"
      />
      <OraMark size={32} className="sm:hidden" />
    </>
  ) : (
    <>
      <span className="hidden sm:inline-flex">
        <Logo light={dark} className="h-8" />
      </span>
      <span className="sm:hidden">
        <OraMark size={32} />
      </span>
    </>
  );

  return (
    <Link
      to="/app/dashboard"
      className={`min-w-0 block rounded-lg -m-1 p-1 transition-colors ${dark ? "hover:bg-white/10" : "hover:bg-[#F8FAFC]"}`}
      aria-label="Go to dashboard"
      data-testid="dashboard-brand-home"
    >
      {mark}
    </Link>
  );
}

const isPathActive = (pathname, item) =>
  item.activePaths?.some((path) =>
    item.end
      ? pathname === path
      : pathname === path || pathname.startsWith(`${path}/`),
  ) || false;

const linkClass = ({ isActive }) =>
  `flex min-h-[36px] items-center gap-2.5 px-3 py-1.5 rounded-lg text-[13.5px] font-medium transition-colors ${
    isActive
      ? "bg-[#F0F6FF] text-[#1D4ED8]"
      : "text-[#475569] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
  }`;

function NavItem({ item, onItemClick }) {
  const Icon = item.icon;
  const { pathname } = useLocation();
  const childSelected = item.children?.some((child) =>
    isPathActive(pathname, child),
  );

  // Entitlement-disabled destinations remain non-interactive; planned product
  // previews are configured as normal links with a truthful label instead.
  if (item.disabled) {
    return (
      <div
        className="flex min-h-[36px] items-center gap-2.5 px-3 py-1.5 rounded-lg text-[13.5px] font-medium text-[#5B6B82] cursor-not-allowed select-none"
        data-testid={item.id}
        aria-disabled="true"
        title="Planned"
      >
        <Icon size={17} />
        <span className="flex-1">{item.label}</span>
        {item.badge && (
          <span className="rounded-full bg-[#F1F5F9] px-2 py-0.5 text-[10px] font-bold text-[#475569]">
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
      className={({ isActive }) =>
        linkClass({ isActive: isActive || isPathActive(pathname, item) })
      }
      aria-current={
        isPathActive(pathname, item) && !childSelected ? "page" : undefined
      }
    >
      <Icon size={17} />
      <span className="flex-1">{item.label}</span>
      {item.badge && (
        <span className="rounded-full bg-[#F1F5F9] px-2 py-0.5 text-[10px] font-bold text-[#475569]">
          {item.badge}
        </span>
      )}
    </NavLink>
  );
}

function SidebarContent({ onItemClick, showClose, onClose, closeButtonRef }) {
  const { isProductEnabled, isFeatureEnabled } = useEntitlements();
  const { organizationName } = useAuth();
  const { pathname } = useLocation();
  const [chatOpen, setChatOpen] = useState(true);

  const groups = NAV_GROUPS.map((g) => ({
    ...g,
    items: filterByEntitlements(g.items, {
      isProductEnabled,
      isFeatureEnabled,
    }),
  })).filter((g) => g.items.length > 0);

  return (
    <>
      {showClose && (
        <>
          <div className="flex h-14 items-center justify-between border-b border-[#E2E8F0] px-4 lg:hidden">
            <BrandHeader />
            <button
              onClick={onClose}
              ref={closeButtonRef}
              className="grid size-11 place-items-center rounded-lg text-[#5B6B82] hover:bg-[#F1F5F9]"
              aria-label="Close menu"
              data-testid="sidebar-close-btn"
            >
              <X size={18} />
            </button>
          </div>
          <div className="px-4 pt-3 lg:hidden">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-[#5B6B82]">
              Workspace
            </p>
            <p className="truncate text-sm font-semibold text-[#0F172A]">
              {organizationName || "Workspace"}
            </p>
          </div>
          <div className="px-3 pb-2 lg:hidden">
            <ProjectSwitcher onNavigate={onItemClick} />
          </div>
        </>
      )}

      <nav className="flex-1 overflow-y-auto p-3 space-y-1 scrollbar-thin">
        {groups.map((group, gi) => (
          <div
            key={group.label || `g-${gi}`}
            className={gi > 0 ? "pt-1.5" : ""}
          >
            {group.label && (
              <p className="px-3 pb-1 pt-1 text-[10px] font-semibold uppercase tracking-[0.09em] text-[#5B6B82]">
                {group.label}
              </p>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <div key={item.to}>
                  <div className="flex items-center">
                    <div className="min-w-0 flex-1">
                      <NavItem item={item} onItemClick={onItemClick} />
                    </div>
                    {item.children && !item.disabled && (
                      <button
                        type="button"
                        onClick={() => setChatOpen((open) => !open)}
                        className="mr-2 grid size-8 shrink-0 place-items-center rounded-lg text-[#5B6B82] transition hover:bg-[#F8FAFC] hover:text-[#0F172A] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563EB]/40"
                        aria-label={`${chatOpen ? "Collapse" : "Expand"} ${item.label} navigation`}
                        aria-expanded={chatOpen}
                      >
                        <ChevronDown
                          size={15}
                          className={`transition-transform ${chatOpen ? "rotate-180" : ""}`}
                        />
                      </button>
                    )}
                  </div>
                  {item.children && chatOpen && (
                    <div className="ml-8 border-l border-[#E2E8F0] pl-2">
                      {item.children.map((child) => (
                        <NavLink
                          key={child.to}
                          to={child.to}
                          end={child.end}
                          data-testid={child.id}
                          onClick={onItemClick}
                          className={({ isActive }) =>
                            `flex min-h-[32px] items-center rounded-md px-3 py-1 text-[13px] transition-colors ${
                              isActive || isPathActive(pathname, child)
                                ? "bg-[#F0F6FF] font-semibold text-[#1D4ED8]"
                                : "text-[#5B6B82] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
                            }`
                          }
                          aria-current={
                            isPathActive(pathname, child) ? "page" : undefined
                          }
                        >
                          {child.label}
                        </NavLink>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-[#E2E8F0] p-3">
        <NavLink
          to="/app/status"
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-[#5B6B82] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
        >
          <span
            className="size-2 rounded-full bg-[#94A3B8]"
            aria-hidden="true"
          />
          System Status
        </NavLink>
        <NavLink
          to="/app/guide"
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-[#5B6B82] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
        >
          Help &amp; Support
        </NavLink>
        <NavLink
          to="/app/products"
          data-testid="nav-product-portfolio"
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-[#5B6B82] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
        >
          Explore all products
        </NavLink>
      </div>
    </>
  );
}

export default function Sidebar({ mobileOpen = false, onClose = () => {} }) {
  const previousFocusRef = useRef(null);
  const closeButtonRef = useRef(null);
  const mobilePanelRef = useRef(null);

  useEffect(() => {
    if (!mobileOpen) {
      previousFocusRef.current?.focus?.();
      previousFocusRef.current = null;
      return undefined;
    }

    previousFocusRef.current = document.activeElement;
    const focusTimer = window.setTimeout(() => {
      closeButtonRef.current?.focus();
    }, 0);
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key === "Tab" && mobilePanelRef.current) {
        const controls = Array.from(
          mobilePanelRef.current.querySelectorAll(
            'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
          ),
        ).filter((control) => control.getClientRects().length > 0);
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (
          first &&
          ((event.shiftKey && document.activeElement === first) ||
            (!event.shiftKey && document.activeElement === last) ||
            !mobilePanelRef.current.contains(document.activeElement))
        ) {
          event.preventDefault();
          (event.shiftKey ? last : first).focus();
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      window.clearTimeout(focusTimer);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [mobileOpen, onClose]);

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden w-[252px] shrink-0 flex-col border-r border-[#E2E8F0] bg-white lg:flex">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
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
            ref={mobilePanelRef}
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
              closeButtonRef={closeButtonRef}
            />
          </aside>
        </div>
      )}
    </>
  );
}
