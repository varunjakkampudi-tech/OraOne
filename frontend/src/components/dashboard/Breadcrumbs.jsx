import React from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { PRIMARY_NAV, SECONDARY_NAV, resolveSection } from "@/constants/navigation";

/* ──────────────────────────────────────────────────────────────────────────
   Breadcrumbs — derived entirely from the navigation config so every page
   gets a consistent trail for free (rendered once in the app shell).
   Trail: Home → Section → Active tab (or a standalone page label).
   ────────────────────────────────────────────────────────────────────────── */

const FLAT = [...PRIMARY_NAV, ...SECONDARY_NAV];

function labelForFlat(pathname) {
  const hit = FLAT.find((n) => pathname === n.to || pathname.startsWith(n.to + "/"));
  return hit?.label || null;
}

export default function Breadcrumbs() {
  const { pathname } = useLocation();

  // Dashboard root shows no breadcrumbs (it's home).
  if (pathname === "/app/dashboard" || pathname === "/app") return null;

  const section = resolveSection(pathname);
  const crumbs = [{ label: "Home", to: "/app/dashboard" }];

  if (section) {
    crumbs.push({ label: section.label, to: section.root });
    // Which tab are we on?
    const tab = section.tabs.find((t) =>
      t.end ? pathname === t.to : pathname === t.to || pathname.startsWith(t.to + "/")
    );
    // Sort by longest match so nested tab wins over the overview tab.
    const best = [...section.tabs]
      .filter((t) => pathname === t.to || pathname.startsWith(t.to + "/"))
      .sort((a, b) => b.to.length - a.to.length)[0];
    const active = best || tab;
    if (active && active.to !== section.root) {
      crumbs.push({ label: active.label });
    } else if (active && active.to === section.root && pathname !== section.root) {
      // deeper detail route under the section root, e.g. /app/agents/:id
      crumbs.push({ label: "Details" });
    }
  } else {
    const label = labelForFlat(pathname);
    if (label) crumbs.push({ label });
  }

  if (crumbs.length < 2) return null;

  return (
    <nav aria-label="Breadcrumb" data-testid="breadcrumbs" className="mb-4">
      <ol className="flex flex-wrap items-center gap-1 text-[12.5px]">
        {crumbs.map((c, i) => {
          const last = i === crumbs.length - 1;
          return (
            <li key={i} className="flex items-center gap-1">
              {c.to && !last ? (
                <Link to={c.to} className="rounded font-medium text-sub transition-colors hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40">
                  {c.label}
                </Link>
              ) : (
                <span aria-current={last ? "page" : undefined} className={last ? "font-semibold text-ink" : "font-medium text-sub"}>
                  {c.label}
                </span>
              )}
              {!last && <ChevronRight size={13} className="text-[#CBD5E1]" aria-hidden="true" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
