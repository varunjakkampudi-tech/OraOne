import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, ChevronDown, Menu, X } from "lucide-react";
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
import type { ReactNode } from "react";

// The shell shared by every public page: a header with five destinations, a mobile
// menu in a dialog (focus is trapped and Escape closes it), and a footer.

function MenuDisclosure({ label, items }: { label: string; items: SiteLink[] }) {
  return (
    <details className="group relative">
      <summary className="flex cursor-pointer list-none items-center gap-1 rounded-md px-3 py-2 text-[15px] font-medium text-foreground hover:bg-muted [&::-webkit-details-marker]:hidden">
        {label}
        <ChevronDown
          className="size-4 transition-transform group-open:rotate-180"
          aria-hidden="true"
        />
      </summary>
      <div className="absolute left-0 top-full z-30 mt-2 grid w-64 gap-1 rounded-xl border border-border bg-background p-2 shadow-xl">
        {items.map((item) => (
          <Link
            key={item.to}
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
        className="lg:hidden"
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
            <Button variant="ghost" size="icon" aria-label="Close menu">
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
                  <li key={item.to}>
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
          <Button asChild variant="outline" size="lg">
            <Link to="/auth/sign-in" onClick={() => setOpen(false)}>
              Sign in
            </Link>
          </Button>
          <Button asChild size="lg">
            <Link to="/auth/sign-in" onClick={() => setOpen(false)}>
              Get started
              <ArrowRight aria-hidden="true" />
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
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-5 md:px-8">
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
          <Button asChild variant="ghost" className="hidden sm:inline-flex">
            <Link to="/auth/sign-in">Sign in</Link>
          </Button>
          <Button asChild className="hidden sm:inline-flex">
            <Link to="/auth/sign-in">
              Get started
              <ArrowRight aria-hidden="true" />
            </Link>
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
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 md:px-8 lg:grid-cols-[1.4fr_repeat(4,1fr)]">
        <div>
          <Brand />
          <p className="mt-4 max-w-xs text-[15px] text-muted-foreground">
            AI chat that answers your customers from your own information.
          </p>
        </div>
        {FOOTER_GROUPS.map((group) => (
          <nav key={group.title} aria-label={group.title}>
            <p className="text-sm font-semibold">{group.title}</p>
            <ul className="mt-4 grid gap-3">
              {group.links.map((item) => (
                <li key={item.to}>
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
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-6 text-sm text-muted-foreground md:px-8">
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
