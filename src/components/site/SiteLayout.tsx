import { useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { ChevronDown, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Brand } from "@/components/oraone/shell";
import {
  FOOTER_GROUPS,
  LEGAL_LINKS,
  PRODUCT_LINKS,
  SOLUTION_LINKS,
  TOP_LINKS,
} from "@/content/site/navigation";
import type { Link as SiteLink } from "@/content/site/types";
import { CONTAINER, PRIMARY_CTA, SECONDARY_CTA } from "./layout";

// The shell shared by every public page. The header, every section and the footer use
// the same container, so all content starts at the logo's left edge.

function MenuDisclosure({ label, items }: { label: string; items: SiteLink[] }) {
  return (
    <details className="group relative">
      <summary className="flex cursor-pointer list-none items-center gap-1 rounded-md px-3 py-2 text-[15px] font-medium hover:bg-muted [&::-webkit-details-marker]:hidden">
        {label}
        <ChevronDown
          className="size-4 transition-transform group-open:rotate-180"
          aria-hidden="true"
        />
      </summary>
      <div className="absolute left-0 top-full z-30 mt-2 grid w-80 gap-1 rounded-xl border border-border bg-background p-2 shadow-xl">
        {items.map((item) => (
          <Link
            key={item.to + item.label}
            to={item.to}
            className="rounded-lg px-3 py-2.5 text-[15px] hover:bg-muted"
          >
            {item.label}
          </Link>
        ))}
      </div>
    </details>
  );
}

function MobileMenu() {
  const [open, setOpen] = useState(false);
  const groups = [
    { title: "Products", items: PRODUCT_LINKS },
    { title: "Solutions", items: SOLUTION_LINKS },
    { title: "Explore", items: TOP_LINKS },
  ];
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button
        variant="ghost"
        size="icon"
        className="size-11 lg:hidden"
        aria-label="Open menu"
        onClick={() => setOpen(true)}
      >
        <Menu className="size-6" aria-hidden="true" />
      </Button>
      <DialogContent className="top-0 left-0 h-dvh max-h-dvh w-full max-w-full translate-x-0 translate-y-0 overflow-y-auto rounded-none p-6">
        <div className="flex items-center justify-between">
          <DialogTitle asChild>
            <span>
              <Brand />
            </span>
          </DialogTitle>
          <DialogClose asChild>
            <Button variant="ghost" size="icon" className="size-11" aria-label="Close menu">
              <X className="size-6" aria-hidden="true" />
            </Button>
          </DialogClose>
        </div>
        <DialogDescription className="sr-only">Site navigation</DialogDescription>
        <nav aria-label="Mobile site navigation" className="mt-8 grid gap-8">
          {groups.map((group) => (
            <div key={group.title}>
              <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {group.title}
              </p>
              <ul className="mt-3 grid gap-1">
                {group.items.map((item) => (
                  <li key={item.to + item.label}>
                    <Link
                      to={item.to}
                      onClick={() => setOpen(false)}
                      className="block rounded-lg px-3 py-3 text-lg font-medium hover:bg-muted"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="mt-10 grid gap-3">
          <Button asChild size="lg" className="h-12 text-base">
            <Link to={PRIMARY_CTA.to} onClick={() => setOpen(false)}>
              {PRIMARY_CTA.label}
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="h-12 text-base">
            <Link to={SECONDARY_CTA.to} onClick={() => setOpen(false)}>
              {SECONDARY_CTA.label}
            </Link>
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
      <div className={`${CONTAINER} flex h-16 items-center justify-between gap-4`}>
        <Link to="/" aria-label="OraOne home" className="shrink-0">
          <Brand />
        </Link>
        <nav aria-label="Main" className="hidden items-center gap-1 lg:flex">
          <MenuDisclosure label="Products" items={PRODUCT_LINKS} />
          <MenuDisclosure label="Solutions" items={SOLUTION_LINKS} />
          {TOP_LINKS.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="rounded-md px-3 py-2 text-[15px] font-medium hover:bg-muted"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" className="hidden h-10 sm:inline-flex">
            <Link to={SECONDARY_CTA.to}>{SECONDARY_CTA.label}</Link>
          </Button>
          <Button asChild className="hidden h-10 sm:inline-flex">
            <Link to={PRIMARY_CTA.to}>{PRIMARY_CTA.label}</Link>
          </Button>
          <MobileMenu />
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-muted/40">
      <div className={`${CONTAINER} grid gap-10 py-12 sm:grid-cols-2 lg:grid-cols-6`}>
        <div className="sm:col-span-2 lg:col-span-2">
          <Brand />
          <p className="mt-4 max-w-sm text-[15px] text-muted-foreground">
            AI chat that answers your customers from your own information, and hands the rest to
            your team.
          </p>
        </div>
        {FOOTER_GROUPS.map((group) => (
          <nav key={group.title} aria-label={group.title}>
            <p className="text-sm font-semibold">{group.title}</p>
            <ul className="mt-4 grid gap-3">
              {group.links.map((item) => (
                <li key={item.to + item.label}>
                  <Link
                    to={item.to}
                    className="text-[15px] text-muted-foreground hover:text-foreground"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <div className="border-t border-border">
        <div
          className={`${CONTAINER} flex flex-wrap items-center justify-between gap-4 py-6 text-sm text-muted-foreground`}
        >
          <p>© 2026 OraOne. All rights reserved.</p>
          <nav aria-label="Legal" className="flex flex-wrap gap-x-5 gap-y-2">
            {LEGAL_LINKS.map((item) => (
              <Link key={item.to} to={item.to} className="hover:text-foreground">
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </footer>
  );
}

export function SiteLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col bg-background text-foreground">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:shadow-lg"
      >
        Skip to content
      </a>
      <SiteHeader />
      <main id="main" className="flex-1">
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}
