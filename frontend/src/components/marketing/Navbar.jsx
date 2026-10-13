import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ChevronDown, Menu, X } from "lucide-react";
import { Logo } from "./Logo";
import { PRODUCT_CATALOG } from "@/constants/productCatalog";
import { NAV } from "@/constants/testIds";

const resources = [
  { label: "Documentation", to: "/documentation" },
  { label: "Help center", to: "/help" },
  { label: "Integrations", to: "/integrations" },
  { label: "Templates", to: "/templates" },
  { label: "Roadmap", to: "/roadmap" },
  { label: "Changelog", to: "/changelog" },
  { label: "Security", to: "/security" },
];
const solutions = [
  { label: "Customer support", to: "/solutions/customer-support" },
  { label: "Lead generation", to: "/solutions/lead-generation" },
  { label: "Sales", to: "/solutions/sales" },
  { label: "Small business", to: "/solutions/small-business" },
  { label: "Enterprise", to: "/solutions/enterprise" },
];
export default function Navbar() {
  const [menu, setMenu] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const header = useRef(null);
  const mobileDialog = useRef(null);
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    setMenu(null);
    setMobileOpen(false);
    const legacyMode = new URLSearchParams(search).get("auth");
    if (legacyMode === "login" || legacyMode === "signup")
      navigate("/" + legacyMode, { replace: true });
  }, [pathname, search, navigate]);
  useEffect(() => {
    const closeOutside = (event) => {
      if (!header.current?.contains(event.target)) setMenu(null);
    };
    const closeEscape = (event) => {
      if (event.key === "Escape") {
        header.current?.querySelector('button[aria-expanded="true"]')?.focus();
        setMenu(null);
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeEscape);
    };
  }, []);
  useEffect(() => {
    const dialog = mobileDialog.current;
    if (mobileOpen && !dialog.open) dialog.showModal();
    if (!mobileOpen && dialog.open) dialog.close();
    if (!mobileOpen) return undefined;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [mobileOpen]);
  const products = PRODUCT_CATALOG.map((product) => ({
    label: product.shortName,
    to: product.id === 1 ? "/products/ai-chat" : "/products/" + product.slug,
    status: product.status,
  }));
  const dropdown = (name, label, items, id) => (
    <div className="relative">
      <button
        type="button"
        data-testid={id}
        aria-expanded={menu === name}
        aria-controls={"marketing-" + name}
        onClick={() => setMenu((current) => (current === name ? null : name))}
        className="inline-flex min-h-11 items-center gap-1.5 rounded-lg px-3 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC] hover:text-[#0F172A]"
      >
        {label}
        <ChevronDown size={14} />
      </button>
      {menu === name && (
        <div
          id={"marketing-" + name}
          className="absolute left-0 top-full z-50 mt-2 max-h-[70vh] w-72 overflow-y-auto rounded-lg border border-[#E2E8F0] bg-white p-2 shadow-lg"
        >
          {items.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              onClick={() => setMenu(null)}
              className="flex min-h-11 items-center justify-between gap-3 rounded-md px-3 py-2 text-sm text-[#334155] hover:bg-[#EFF6FF] hover:text-[#2563EB]"
            >
              <span>{item.label}</span>
              {item.status && (
                <span className="text-[11px] text-[#64748B]">
                  {item.status}
                </span>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
  return (
    <header
      ref={header}
      className="fixed inset-x-0 top-0 z-40 border-b border-[#E2E8F0] bg-white"
    >
      <div className="mx-auto flex h-16 max-w-[1184px] items-center justify-between gap-4 px-5 sm:px-8">
        <Link
          to="/"
          className="shrink-0"
          data-testid="navbar-brand-link"
          aria-label="OraOne home"
        >
          <Logo className="h-9 w-auto" />
        </Link>
        <nav
          className="hidden items-center gap-2 lg:flex"
          aria-label="Main navigation"
        >
          {dropdown("products", "Products", products, NAV.productsMenu)}
          {dropdown("solutions", "Solutions", solutions, NAV.solutionsMenu)}
          <Link
            to="/pricing"
            data-testid={NAV.pricingLink}
            className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm font-medium text-[#475569] hover:bg-[#F8FAFC]"
          >
            Pricing
          </Link>
          {dropdown("resources", "Resources", resources, "nav-resources-menu")}
        </nav>
        <div className="flex items-center gap-2">
          <Link
            to="/login"
            data-testid={NAV.loginBtn}
            className="hidden min-h-11 items-center px-3 text-sm font-medium text-[#475569] sm:inline-flex"
          >
            Sign in
          </Link>
          <Link
            to="/signup"
            data-testid={NAV.startFreeBtn}
            className="inline-flex min-h-11 items-center rounded-lg bg-[#2563EB] px-4 text-sm font-semibold text-white hover:bg-[#1D4ED8]"
          >
            Get started
          </Link>
          <button
            type="button"
            data-testid={NAV.mobileToggle}
            onClick={() => setMobileOpen(true)}
            className="grid size-11 place-items-center rounded-lg text-[#0F172A] hover:bg-[#F1F5F9] lg:hidden"
            aria-label="Open menu"
            aria-expanded={mobileOpen}
            aria-controls="marketing-mobile-navigation"
          >
            <Menu size={21} />
          </button>
        </div>
      </div>
      <dialog
        id="marketing-mobile-navigation"
        ref={mobileDialog}
        onCancel={() => setMobileOpen(false)}
        onClose={() => setMobileOpen(false)}
        className="fixed inset-0 m-0 h-dvh max-h-none w-[min(360px,100vw)] max-w-none border-0 bg-white p-5 text-[#0F172A] backdrop:bg-[#0F172A]/50"
      >
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold">OraOne navigation</h2>
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
            className="grid size-11 place-items-center rounded-lg hover:bg-[#F1F5F9]"
          >
            <X size={22} />
          </button>
        </div>
        <nav
          aria-label="Mobile navigation"
          className="mt-6 flex flex-col gap-1"
        >
          {[
            { label: "Products", to: "/products" },
            { label: "Solutions", to: "/solutions" },
            { label: "Pricing", to: "/pricing" },
            ...resources,
          ].map((item) => (
            <Link
              key={item.to}
              to={item.to}
              onClick={() => setMobileOpen(false)}
              className="min-h-11 border-b border-[#F1F5F9] py-3 text-sm font-medium"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mt-6 grid gap-3">
          <Link
            to="/login"
            onClick={() => setMobileOpen(false)}
            className="rounded-lg border border-[#E2E8F0] px-4 py-3 text-center text-sm font-semibold"
          >
            Sign in
          </Link>
          <Link
            to="/signup"
            onClick={() => setMobileOpen(false)}
            className="rounded-lg bg-[#2563EB] px-4 py-3 text-center text-sm font-semibold text-white"
          >
            Create account
          </Link>
        </div>
      </dialog>
    </header>
  );
}
