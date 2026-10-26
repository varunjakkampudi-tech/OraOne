import { useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import {
  ArrowRight,
  BookOpen,
  Check,
  CircleCheck,
  Clock,
  Hammer,
  MessageSquare,
  Sparkles,
  Users,
  Waypoints,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { DOCS_TREE, STATUS_LABEL } from "@/content/site/navigation";
import { PORTFOLIO } from "@/content/site/portfolio";
import type {
  ArticlePage,
  Capability,
  DocsPage,
  Faq,
  FormPage,
  HubPage,
  LandingPage,
  Link as SiteLink,
  ListPage,
  PricingPage,
  ProductPage,
  SitePage,
  Status,
  Step,
  UseCase,
} from "@/content/site/types";
import { SiteLayout } from "./SiteLayout";
import { CONTAINER, PRIMARY_CTA, SECTION_Y } from "./layout";
import { capabilityIcon, industryIcon, productIcon, stepIcon } from "./icons";
import { IconTile } from "./IconTile";
import { SCREENS, solutionImage } from "./images";

// One template per page kind. Every page uses the same container, spacing, type scale and
// status labels, so the public site reads as one product.

const STATUS_ICON: Record<Status, typeof CircleCheck> = {
  available: CircleCheck,
  active: Hammer,
  beta: Sparkles,
  "in-development": Hammer,
  planned: Clock,
  vision: Waypoints,
};

const STATUS_STYLE: Record<Status, string> = {
  available: "bg-emerald-50 text-emerald-900 ring-emerald-300",
  active: "bg-sky-100 text-sky-950 ring-sky-400",
  beta: "bg-violet-50 text-violet-900 ring-violet-300",
  "in-development": "bg-amber-50 text-amber-950 ring-amber-300",
  planned: "bg-background text-slate-700 ring-slate-300",
  vision: "bg-background text-slate-600 ring-slate-300 ring-dashed",
};

export function StatusBadge({ status }: { status: Status }) {
  const Icon = STATUS_ICON[status];
  return (
    <span
      className={`inline-flex h-7 items-center gap-1.5 whitespace-nowrap rounded-full px-3 text-sm font-medium ring-1 ring-inset ${STATUS_STYLE[status]}`}
    >
      <Icon className="size-4 shrink-0" aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  );
}

function Eyebrow({ children, dark = false }: { children: ReactNode; dark?: boolean }) {
  return (
    <p
      className={`text-sm font-semibold uppercase tracking-wider ${dark ? "text-sky-300" : "text-primary"}`}
    >
      {children}
    </p>
  );
}

function Section({
  id,
  title,
  lead,
  children,
  muted = false,
}: {
  id?: string;
  title?: string;
  lead?: string;
  children: ReactNode;
  muted?: boolean;
}) {
  return (
    <section id={id} className={`scroll-mt-20 ${SECTION_Y} ${muted ? "bg-muted/40" : ""}`}>
      <div className={CONTAINER}>
        {title && (
          <div className="max-w-2xl">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">{title}</h2>
            {lead && <p className="mt-3 text-[17px] leading-relaxed text-foreground/75">{lead}</p>}
          </div>
        )}
        <div className={title ? "mt-8" : ""}>{children}</div>
      </div>
    </section>
  );
}

function PrimaryLink({ link }: { link: SiteLink }) {
  return (
    <Button asChild size="lg" className="h-12 px-6 text-base">
      <Link to={link.to}>
        {link.label}
        <ArrowRight aria-hidden="true" />
      </Link>
    </Button>
  );
}

function SecondaryLink({ link, dark = false }: { link: SiteLink; dark?: boolean }) {
  return (
    <Button
      asChild
      variant="outline"
      size="lg"
      className={`h-12 px-6 text-base ${dark ? "border-white/40 bg-transparent text-white hover:bg-white/10 hover:text-white" : ""}`}
    >
      <Link to={link.to}>{link.label}</Link>
    </Button>
  );
}

/** A small diagram of how a question moves through OraOne. Illustrative; contains no data. */
function FlowDiagram({ dark = false }: { dark?: boolean }) {
  const node = dark
    ? "border-white/15 bg-white/5 text-white"
    : "border-border bg-background text-foreground";
  const muted = dark ? "text-slate-300" : "text-foreground/75";
  return (
    <figure
      role="img"
      aria-label="Illustration: a visitor's question goes to the OraOne assistant, which answers from your documents or passes it to your team"
      className={`rounded-2xl border p-6 md:p-8 ${dark ? "border-white/10 bg-slate-900" : "border-border bg-muted/40"}`}
    >
      <div className="grid gap-4">
        <div className={`rounded-xl border p-4 ${node}`}>
          <p className="font-semibold">Visitor asks a question</p>
          <p className={`mt-1 text-base md:text-[15px] ${muted}`}>On your website, at any hour</p>
        </div>
        <div className="flex justify-center" aria-hidden="true">
          <div className={`h-6 w-px ${dark ? "bg-white/30" : "bg-slate-300"}`} />
        </div>
        <div
          className={`rounded-xl border-2 p-4 ${dark ? "border-sky-400 bg-sky-400/10" : "border-primary bg-primary/5"}`}
        >
          <p className="font-semibold">OraOne assistant</p>
          <p className={`mt-1 text-base md:text-[15px] ${muted}`}>
            Answers from your documents and cites its sources
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className={`rounded-xl border p-4 ${node}`}>
            <p className="font-semibold">Answered</p>
            <p className={`mt-1 text-base md:text-[15px] ${muted}`}>
              The visitor gets a clear reply
            </p>
          </div>
          <div className={`rounded-xl border p-4 ${node}`}>
            <p className="font-semibold">Handed to your team</p>
            <p className={`mt-1 text-base md:text-[15px] ${muted}`}>
              Lead and history in the inbox
            </p>
          </div>
        </div>
      </div>
    </figure>
  );
}

function BrowserFrame({ src, alt }: { src: string; alt: string }) {
  return (
    <figure className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900 shadow-2xl shadow-black/50 ring-1 ring-white/5">
      <div
        className="flex items-center gap-1.5 border-b border-white/10 bg-slate-800/80 px-4 py-3"
        aria-hidden="true"
      >
        <span className="size-2.5 rounded-full bg-slate-600" />
        <span className="size-2.5 rounded-full bg-slate-600" />
        <span className="size-2.5 rounded-full bg-slate-600" />
        <span className="ml-3 h-5 flex-1 rounded-md bg-slate-900/80" />
      </div>
      <img
        src={src}
        alt={alt}
        width={1280}
        height={800}
        loading="eager"
        decoding="async"
        className="block h-auto w-full"
      />
    </figure>
  );
}

/** A visitor conversation on a website, with example data. It shows the answer, its source and the saved lead. */
function ChatDemo() {
  return (
    <figure
      className="overflow-hidden rounded-2xl border border-white/10 bg-slate-900 shadow-2xl shadow-black/50 ring-1 ring-white/5"
      aria-label="Example visitor conversation on a clinic website"
    >
      <figcaption className="flex items-center justify-between border-b border-white/10 bg-slate-800/80 px-5 py-3 text-sm text-slate-300">
        <span className="font-medium text-white">Clinic website chat</span>
        <span className="text-xs text-slate-400">Example conversation</span>
      </figcaption>
      <div className="flex flex-col gap-4 p-5 text-base md:text-[15px] leading-relaxed">
        <p className="ml-auto max-w-[80%] rounded-2xl rounded-br-sm bg-sky-500 px-4 py-2.5 text-white">
          What are your opening hours on Saturday?
        </p>
        <div className="max-w-[88%]">
          <p className="rounded-2xl rounded-bl-sm bg-white/10 px-4 py-2.5 text-slate-100">
            We are open from 9am to 1pm on Saturdays.
          </p>
          <p className="mt-1.5 pl-1 text-xs text-slate-400">Source: clinic FAQ</p>
        </div>
        <p className="ml-auto max-w-[80%] rounded-2xl rounded-br-sm bg-sky-500 px-4 py-2.5 text-white">
          Can I book a clean and check-up?
        </p>
        <div className="max-w-[88%]">
          <p className="rounded-2xl rounded-bl-sm bg-white/10 px-4 py-2.5 text-slate-100">
            I can take your name, phone number and a preferred time. The team confirms the booking.
          </p>
        </div>
        <p className="ml-auto max-w-[80%] rounded-2xl rounded-br-sm bg-sky-500 px-4 py-2.5 text-white">
          This is Visitor A. Call me on 555 0100 on Saturday morning.
        </p>
        <div className="max-w-[88%]">
          <p className="rounded-2xl rounded-bl-sm bg-white/10 px-4 py-2.5 text-slate-100">
            Thanks, Visitor A. The team will confirm your Saturday appointment.
          </p>
        </div>
        <div className="mt-1 flex items-center justify-between gap-3 rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm">
          <span className="text-emerald-100">Lead saved to the inbox</span>
          <span className="rounded-full bg-emerald-400/20 px-2.5 py-0.5 text-xs font-medium text-emerald-100">
            New
          </span>
        </div>
      </div>
    </figure>
  );
}

function Hero({
  eyebrow,
  title,
  lead,
  primary,
  secondary,
  note,
  screen,
  screenAlt,
  visual,
}: {
  eyebrow?: string;
  title: string;
  lead: string;
  primary: SiteLink;
  secondary?: SiteLink | undefined;
  note?: string | undefined;
  screen: string;
  screenAlt: string;
  visual?: ReactNode;
}) {
  return (
    <section className="relative isolate overflow-hidden bg-slate-950 text-white">
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-[radial-gradient(60%_80%_at_85%_20%,rgba(56,189,248,0.22),transparent_70%),radial-gradient(50%_60%_at_10%_90%,rgba(21,93,252,0.25),transparent_70%)]"
      />
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-gradient-to-r from-slate-950 via-slate-950/80 to-slate-950/40"
      />
      <div
        className={`${CONTAINER} grid items-center gap-12 py-16 md:py-20 lg:grid-cols-12 lg:py-24`}
      >
        <div className="lg:col-span-5">
          {eyebrow && (
            <p className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-sm font-medium text-sky-200">
              <span className="size-1.5 rounded-full bg-sky-400" aria-hidden="true" />
              {eyebrow}
            </p>
          )}
          <h1 className="mt-6 text-5xl font-bold leading-[1.05] tracking-tight text-balance md:text-6xl xl:text-7xl">
            {title}
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-slate-300 md:text-xl">{lead}</p>
          <div className="mt-10 flex flex-col gap-3 sm:flex-row">
            <Button
              asChild
              size="lg"
              className="h-12 bg-sky-500 px-6 text-base text-white hover:bg-sky-400"
            >
              <Link to={primary.to}>
                {primary.label}
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
            {secondary && (
              <Button
                asChild
                variant="outline"
                size="lg"
                className="h-12 border-white/25 bg-transparent px-6 text-base text-white hover:bg-white/10 hover:text-white"
              >
                <Link to={secondary.to}>{secondary.label}</Link>
              </Button>
            )}
          </div>
          {note && <p className="mt-6 max-w-xl text-base md:text-[15px] text-slate-400">{note}</p>}
        </div>
        <div className="lg:col-span-7">
          {visual ?? <BrowserFrame src={screen} alt={screenAlt} />}
        </div>
      </div>
    </section>
  );
}

function CapabilityGrid({ items }: { items: Capability[] }) {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <li
          key={item.title}
          className="flex flex-col gap-4 rounded-xl border border-border bg-background p-6 shadow-sm transition-shadow hover:shadow-md"
        >
          <div className="flex items-start justify-between gap-3">
            <IconTile icon={capabilityIcon(item.title)} />
            <StatusBadge status={item.status} />
          </div>
          <h3 className="text-xl font-semibold">{item.title}</h3>
          <p className="text-[17px] leading-relaxed text-foreground/75">{item.text}</p>
        </li>
      ))}
    </ul>
  );
}

const FEATURE_TITLES = new Set([
  "Website chat",
  "Answers from your documents",
  "Team inbox and leads",
]);

/** Compact, real-looking interface previews for the feature cards. Example data only. */
function FeaturePreview({ title }: { title: string }) {
  if (title === "Website chat") {
    return (
      <div className="flex h-full flex-col justify-between gap-4 p-5" aria-hidden="true">
        <div className="space-y-3">
          <p className="text-sm font-semibold text-foreground">Clinic website chat</p>
          <p className="max-w-[85%] rounded-2xl rounded-bl-sm bg-muted px-3 py-2 text-sm text-foreground">
            Do you open on Saturdays?
          </p>
          <div className="max-w-[90%]">
            <p className="rounded-2xl rounded-bl-sm bg-primary px-3 py-2 text-sm text-primary-foreground">
              Yes, from 9am to 1pm.
            </p>
            <p className="mt-1 pl-1 text-xs text-foreground/70">Source: Clinic information.pdf</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-border px-3 py-1.5">
          <span className="flex-1 text-sm text-foreground/70">Type a message</span>
          <span className="size-6 rounded-full bg-primary" />
        </div>
      </div>
    );
  }
  if (title === "Answers from your documents") {
    const files = [
      ["Clinic information.pdf", "Indexed"],
      ["Treatments and prices.docx", "Indexed"],
      ["FAQ.txt", "Processing"],
    ];
    return (
      <div className="flex h-full flex-col gap-3 p-5" aria-hidden="true">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-foreground">Knowledge</p>
          <span className="rounded-md border border-border px-2 py-0.5 text-xs text-foreground/70">
            3 files
          </span>
        </div>
        <ul className="grid gap-2">
          {files.map(([name, state]) => (
            <li
              key={name}
              className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-sm"
            >
              <span className="truncate text-foreground">{name}</span>
              <span className="shrink-0 text-xs text-foreground/70">{state}</span>
            </li>
          ))}
        </ul>
        <p className="mt-auto rounded-lg bg-muted px-3 py-2 text-xs text-foreground/85">
          Answers cite the file they came from.
        </p>
      </div>
    );
  }
  if (title === "Team inbox and leads") {
    const rows = [
      ["Visitor A", "Lead: Saturday morning", "New", "10:24"],
      ["Visitor B", "Do you accept new patients?", "Answered", "Yesterday"],
      ["Visitor C", "Opening hours on Saturdays", "Answered", "Yesterday"],
      ["Visitor D", "Is there parking at the clinic?", "Answered", "Mon"],
    ];
    return (
      <div className="flex h-full flex-col gap-3 p-5" aria-hidden="true">
        <p className="text-sm font-semibold text-foreground">Inbox</p>
        <ul className="grid gap-2">
          {rows.map(([name, text, status, time], index) => (
            <li
              key={name}
              className={`flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-sm ${index === 0 ? "bg-primary/5" : ""}`}
            >
              <span className="min-w-0">
                <span className="block font-medium text-foreground">{name}</span>
                <span className="block truncate text-foreground/75">{text}</span>
              </span>
              <span className="flex shrink-0 flex-col items-end gap-1 text-xs text-foreground/70">
                <span
                  className={`rounded-full px-2 py-0.5 ${status === "New" ? "bg-emerald-100 text-emerald-900" : "bg-muted text-foreground"}`}
                >
                  {status}
                </span>
                {time}
              </span>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  return null;
}

function FeatureRows({ items }: { items: Capability[] }) {
  return (
    <ul className="-mx-4 flex snap-x snap-mandatory gap-4 overflow-x-auto px-4 pb-2 md:mx-0 md:grid md:grid-cols-2 md:gap-6 md:overflow-visible md:px-0 lg:grid-cols-3">
      {items.map((item) => (
        <li
          key={item.title}
          className="flex w-[82%] shrink-0 snap-start flex-col gap-5 md:w-auto md:shrink md:last:col-span-2 lg:last:col-span-1"
        >
          <div className="overflow-hidden rounded-2xl border border-border bg-background shadow-lg lg:aspect-[4/3]">
            <FeaturePreview title={item.title} />
          </div>
          <div>
            <StatusBadge status={item.status} />
            <h3 className="mt-3 text-2xl font-bold tracking-tight">{item.title}</h3>
            <p className="mt-2 text-[17px] leading-relaxed text-foreground/80">{item.text}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function Steps({ steps }: { steps: Step[] }) {
  return (
    <ol className="grid gap-4 md:grid-cols-3">
      {steps.map((step, index) => (
        <li
          key={step.title}
          className="relative flex flex-col gap-4 rounded-xl border border-border bg-background p-6 shadow-sm"
        >
          <div className="flex items-center gap-3">
            <IconTile icon={stepIcon(index)} tone="muted" />
            <span className="text-sm font-semibold uppercase tracking-wide text-foreground/75">
              Step {index + 1}
            </span>
          </div>
          <h3 className="text-xl font-semibold">{step.title}</h3>
          <p className="text-[17px] leading-relaxed text-foreground/75">{step.text}</p>
        </li>
      ))}
    </ol>
  );
}

function UseCaseGrid({ items }: { items: UseCase[] }) {
  return (
    <ul className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => {
        return (
          <li
            key={item.industry}
            className="flex flex-col rounded-2xl border border-border bg-background p-6 shadow-sm md:last:col-span-2 lg:last:col-span-1"
          >
            <div className="flex flex-1 flex-col gap-3">
              <p className="text-sm font-semibold uppercase tracking-wide text-primary">
                {item.industry}
              </p>
              <h3 className="text-xl font-semibold leading-snug">{item.problem}</h3>
              <p className="text-[17px] leading-relaxed text-foreground/75">
                <span className="font-medium text-foreground">The assistant </span>
                {item.assistant}
              </p>
              <p className="text-[17px] leading-relaxed text-foreground/75">
                <span className="font-medium text-foreground">Your team </span>
                {item.team}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function Faqs({ items }: { items: Faq[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 md:items-start">
      {items.map((item) => (
        <details key={item.q} className="group rounded-xl border border-border px-5 py-4">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-lg font-semibold [&::-webkit-details-marker]:hidden">
            {item.q}
            <span
              aria-hidden="true"
              className="text-2xl leading-none text-foreground/75 transition-transform group-open:rotate-45"
            >
              +
            </span>
          </summary>
          <p className="mt-3 text-[17px] leading-relaxed text-foreground/75">{item.a}</p>
        </details>
      ))}
    </div>
  );
}

/** The complete OraOne family, one row per product, with an honest status on each. */
export function ProductFamily({ id = "products", dark = false }: { id?: string; dark?: boolean }) {
  const muted = dark ? "text-slate-300" : "text-foreground/75";
  const box = dark ? "border-white/10 bg-white/5" : "border-border bg-background";
  const groups: { title: string; note: string; items: typeof PORTFOLIO }[] = [
    {
      title: "In active development",
      note: "Usable in the demo today. Not yet generally available.",
      items: PORTFOLIO.filter((p) => p.status === "active"),
    },
    {
      title: "Coming next",
      note: "On the roadmap. No dates are promised.",
      items: PORTFOLIO.filter((p) => p.status === "planned"),
    },
    {
      title: "Longer term",
      note: "Where the platform is heading.",
      items: PORTFOLIO.filter((p) => p.status === "vision"),
    },
  ];
  return (
    <section
      id={id}
      className={`scroll-mt-20 ${SECTION_Y} ${dark ? "bg-slate-950 text-white" : ""}`}
      aria-labelledby={`${id}-heading`}
    >
      <div className={CONTAINER}>
        <div className="max-w-2xl">
          <p
            className={`text-sm font-semibold uppercase tracking-wider ${dark ? "text-sky-300" : "text-primary"}`}
          >
            One platform
          </p>
          <h2 id={`${id}-heading`} className="mt-3 text-3xl font-bold tracking-tight md:text-4xl">
            One AI for every conversation
          </h2>
          <p className={`mt-3 text-[17px] leading-relaxed ${muted}`}>
            Every capability works with the same account, knowledge and inbox. Anything not yet
            available is labelled as such.
          </p>
        </div>
        <div className="mt-10 grid gap-10">
          {groups.map((group) => (
            <div key={group.title}>
              <h3 className="text-lg font-semibold">{group.title}</h3>
              <p className={`text-base md:text-[15px] ${muted}`}>{group.note}</p>
              <ul className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {group.items.map((product) => (
                  <li
                    key={product.id}
                    className={`flex items-center gap-3 rounded-xl border p-3 sm:gap-4 sm:p-4 ${box}`}
                  >
                    <IconTile
                      icon={productIcon(product.id)}
                      tone={product.status === "active" ? "brand" : "muted"}
                    />
                    <div className="min-w-0 flex-1">
                      <Link
                        to={product.id === 1 ? "/products/ai-chat" : "/roadmap"}
                        className="font-semibold hover:text-primary hover:underline"
                      >
                        {product.capability}
                      </Link>
                      <div className="mt-1">
                        <StatusBadge status={product.status} />
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CtaBand({ title, text, primary }: { title: string; text: string; primary: SiteLink }) {
  return (
    <section className="py-12 md:py-16">
      <div className={CONTAINER}>
        <div className="flex flex-col items-start justify-between gap-6 rounded-2xl bg-slate-950 p-8 text-white lg:flex-row lg:items-center md:p-12">
          <div className="max-w-2xl">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">{title}</h2>
            <p className="mt-3 text-lg text-slate-300">{text}</p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button
              asChild
              size="lg"
              className="h-12 bg-white px-6 text-base text-slate-950 hover:bg-slate-100"
            >
              <Link to={primary.to}>
                {primary.label}
                <ArrowRight aria-hidden="true" />
              </Link>
            </Button>
            <Link
              to="/contact"
              className="inline-flex min-h-11 items-center whitespace-nowrap px-2 text-base font-medium text-slate-200 underline-offset-4 hover:text-white hover:underline"
            >
              Talk to the team
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

/** The team view of the same booking conversation shown in the hero: the thread and the captured lead. Example data only. */
function InboxPreview() {
  const rows = [
    { q: "Can I book a clean and check-up?", status: "Lead", time: "08:52", active: true },
    {
      q: "What are your opening hours on Saturday?",
      status: "Answered",
      time: "09:14",
      active: false,
    },
    { q: "Do you accept new patients?", status: "Answered", time: "Yesterday", active: false },
  ];
  return (
    <figure
      className="overflow-hidden rounded-2xl border border-border bg-background shadow-xl shadow-slate-900/10"
      aria-label="Example team inbox showing the booking conversation and the captured lead"
    >
      <div className="grid md:grid-cols-2 lg:grid-cols-12">
        <ul className="border-b border-border md:border-b-0 md:border-r lg:col-span-4">
          <li className="px-5 py-4 text-sm font-semibold text-foreground">Conversations</li>
          {rows.map((row) => (
            <li
              key={row.q}
              className={`border-t border-border px-5 py-4 ${row.active ? "bg-primary/5" : ""}`}
            >
              <p className="text-base md:text-[15px] font-medium text-foreground">{row.q}</p>
              <div className="mt-1 flex items-center justify-between text-xs text-foreground/70">
                <span>{row.status}</span>
                <span>{row.time}</span>
              </div>
            </li>
          ))}
        </ul>
        <div className="hidden flex-col gap-3 p-6 lg:col-span-5 lg:flex">
          <p className="text-sm font-semibold text-foreground">Clinic website chat</p>
          <p className="max-w-[85%] rounded-2xl rounded-bl-sm bg-muted px-4 py-2.5 text-base md:text-[15px] text-foreground">
            Can I book a clean and check-up?
          </p>
          <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-base md:text-[15px] text-primary-foreground">
            I can take your name, phone number and a preferred time.
          </p>
          <p className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-muted px-4 py-2.5 text-base md:text-[15px] text-foreground">
            This is Visitor A. Call me on 555 0100 on Saturday morning.
          </p>
          <p className="max-w-[85%] rounded-2xl rounded-bl-sm bg-primary px-4 py-2.5 text-base md:text-[15px] text-primary-foreground">
            Thanks, Visitor A. The team will confirm your Saturday appointment.
          </p>
        </div>
        <aside className="border-t border-border p-6 md:border-l md:border-t-0 lg:col-span-3">
          <p className="text-sm font-semibold text-foreground">Captured lead</p>
          <dl className="mt-4 grid gap-3 text-sm">
            <div>
              <dt className="text-foreground/70">Name</dt>
              <dd className="font-medium text-foreground">Visitor A</dd>
            </div>
            <div>
              <dt className="text-foreground/70">Phone</dt>
              <dd className="font-medium text-foreground">555 0100</dd>
            </div>
            <div>
              <dt className="text-foreground/70">Preferred time</dt>
              <dd className="font-medium text-foreground">Saturday morning</dd>
            </div>
            <div>
              <dt className="text-foreground/70">Status</dt>
              <dd className="mt-1">
                <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-900">
                  Awaiting team confirmation
                </span>
              </dd>
            </div>
          </dl>
        </aside>
      </div>
    </figure>
  );
}

function Showcase() {
  return (
    <Section
      title="From the chat to the team inbox"
      lead="Conversations from your website are kept in one inbox, with the leads they capture. Example data from the demo workspace."
    >
      <InboxPreview />
    </Section>
  );
}

function LandingTemplate({ page }: { page: LandingPage }) {
  return (
    <>
      <Hero
        eyebrow={page.eyebrow}
        title={page.hero.title}
        lead={page.hero.lead}
        primary={page.hero.primary}
        secondary={page.hero.secondary}
        note={page.hero.note}
        screen={SCREENS.inbox}
        screenAlt="The OraOne team inbox with conversations and their history"
        visual={<ChatDemo />}
      />
      <Section
        title="Better customer conversations."
        lead="OraOne answers customer questions from your content and hands complex or unanswered enquiries to your team, in one connected conversation."
        muted
      >
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              icon: Zap,
              title: "Faster responses",
              text: "Customers get answers from your content as soon as they ask.",
            },
            {
              icon: BookOpen,
              title: "Grounded in your content",
              text: "Answers come from your website, documents and resources.",
            },
            {
              icon: Users,
              title: "Seamless handoffs",
              text: "Complex or unanswered enquiries pass to your team with the details.",
            },
            {
              icon: MessageSquare,
              title: "One shared conversation flow",
              text: "The full context stays with the person who replies.",
            },
          ].map((item) => (
            <li
              key={item.title}
              className="flex flex-col gap-3 rounded-xl border border-border bg-background p-6 shadow-sm"
            >
              <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <item.icon className="size-5" aria-hidden="true" />
              </span>
              <h3 className="text-lg font-semibold">{item.title}</h3>
              <p className="text-[16px] leading-relaxed text-foreground/75">{item.text}</p>
            </li>
          ))}
        </ul>
      </Section>
      {page.showcase && <Showcase />}
      {page.steps.length > 0 && (
        <Section
          title="How it works"
          lead="Three steps. A developer is only needed if you add the chat with code."
          muted
        >
          <Steps steps={page.steps} />
        </Section>
      )}
      {page.capabilities.some((c) => FEATURE_TITLES.has(c.title)) && (
        <Section title="Built for the way customers ask" lead="Each feature shows its real status.">
          <FeatureRows items={page.capabilities.filter((c) => FEATURE_TITLES.has(c.title))} />
        </Section>
      )}
      {page.useCases.length > 0 && (
        <Section
          title="Where it helps"
          lead="Illustrative examples of how a business might use an assistant. They describe the intended workflow, not real customers or results."
          muted
        >
          <UseCaseGrid items={page.useCases.slice(0, 3)} />
        </Section>
      )}
      <ProductFamily dark />
      {page.faqs.length > 0 && (
        <Section title="Common questions" muted>
          <div className="max-w-3xl">
            <Faqs items={page.faqs} />
          </div>
        </Section>
      )}
      <CtaBand title={page.cta.title} text={page.cta.text} primary={page.cta.primary} />
    </>
  );
}

function ProductTemplate({ page }: { page: ProductPage }) {
  return (
    <>
      <Hero
        eyebrow={page.eyebrow}
        title={page.hero.title}
        lead={page.hero.lead}
        primary={page.hero.primary}
        secondary={page.hero.secondary}
        screen={SCREENS.assistant}
        screenAlt="The OraOne assistant editor with instructions and knowledge"
      />
      {page.showcase && <Showcase />}
      <Section title="The problem it solves">
        <p className="max-w-3xl text-xl leading-relaxed">{page.problem}</p>
        <ul className="mt-6 grid gap-4 md:grid-cols-3">
          {page.outcomes.map((item) => (
            <li key={item} className="flex items-start gap-3 rounded-xl border border-border p-5">
              <Check className="mt-1 size-5 shrink-0 text-primary" aria-hidden="true" />
              <span className="text-[17px]">{item}</span>
            </li>
          ))}
        </ul>
      </Section>
      {page.capabilities.length > 0 && (
        <Section title="Features" muted>
          <CapabilityGrid items={page.capabilities} />
        </Section>
      )}
      {page.useCases.length > 0 && (
        <Section
          title="Where it helps"
          lead="Illustrative examples, not real customers or results."
        >
          <UseCaseGrid items={page.useCases} />
        </Section>
      )}
      {page.steps.length > 0 && (
        <Section title="Getting started">
          <Steps steps={page.steps} />
        </Section>
      )}
      {page.faqs.length > 0 && (
        <Section title="Questions" muted>
          <div className="max-w-3xl">
            <Faqs items={page.faqs} />
          </div>
        </Section>
      )}
      <CtaBand title={page.cta.title} text={page.cta.text} primary={page.cta.primary} />
    </>
  );
}

function PricingTemplate({ page }: { page: PricingPage }) {
  return (
    <>
      <section className={SECTION_Y}>
        <div className={CONTAINER}>
          <div className="max-w-3xl">
            <Eyebrow>{page.eyebrow}</Eyebrow>
            <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-5xl">
              Free access during development
            </h1>
            <p className="mt-4 text-lg leading-relaxed text-foreground/75">{page.lead}</p>
          </div>
          <div className="mt-8 grid gap-4 lg:max-w-3xl">
            {page.plans.map((plan) => (
              <article key={plan.name} className="rounded-2xl border border-primary/40 p-6 md:p-8">
                <div className="flex flex-wrap items-baseline justify-between gap-4">
                  <h2 className="text-2xl font-semibold">{plan.name}</h2>
                  <p className="text-4xl font-bold">{plan.price}</p>
                </div>
                <p className="mt-2 text-[17px] text-foreground/75">{plan.summary}</p>
                <ul className="mt-6 grid gap-3 sm:grid-cols-2">
                  {plan.items.map((item) => (
                    <li key={item} className="flex items-start gap-3 text-[17px]">
                      <Check className="mt-1 size-5 shrink-0 text-primary" aria-hidden="true" />
                      {item}
                    </li>
                  ))}
                </ul>
                <div className="mt-8">
                  <PrimaryLink link={plan.cta} />
                </div>
              </article>
            ))}
          </div>
          <ul className="mt-8 grid gap-2 text-[17px] text-foreground/75 lg:max-w-3xl">
            {page.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      </section>
      <Section title="Questions" muted>
        <div className="max-w-3xl">
          <Faqs items={page.faqs} />
        </div>
      </Section>
    </>
  );
}

function DocsTemplate({ page }: { page: DocsPage }) {
  return (
    <div
      className={`${CONTAINER} grid grid-cols-1 gap-10 py-12 lg:grid-cols-[14rem_minmax(0,1fr)] lg:py-16`}
    >
      <aside
        aria-label="Documentation"
        className="min-w-0 max-w-full overflow-hidden lg:sticky lg:top-24 lg:self-start lg:overflow-visible"
      >
        <nav className="grid gap-6 max-lg:-mx-1 max-lg:flex max-lg:gap-6 max-lg:overflow-x-auto max-lg:pb-2">
          {DOCS_TREE.map((group) => (
            <div key={group.group}>
              <p className="text-sm font-semibold uppercase tracking-wide text-foreground/75 max-lg:hidden">
                {group.group}
              </p>
              <ul className="mt-2 grid gap-1 max-lg:mt-0 max-lg:flex max-lg:shrink-0 max-lg:gap-2">
                {group.links.map((item) => (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      aria-current={item.to === page.path ? "page" : undefined}
                      className={`block rounded-lg px-3 py-2 text-base md:text-[15px] ${item.to === page.path ? "bg-accent font-semibold text-accent-foreground" : "hover:bg-muted"}`}
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      </aside>
      <article className="min-w-0 max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-wide text-primary">{page.group}</p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight md:text-5xl">
          {page.title.split(" | ")[0]}
        </h1>
        <p
          role="note"
          className="mt-6 rounded-xl border border-border bg-muted/50 p-4 text-[16px] text-foreground/85"
        >
          Documentation status: AI Chat is in active development. These guides describe the intended
          setup. Steps are not yet verified for production use.
        </p>
        <p className="mt-4 text-xl leading-relaxed text-foreground/75">{page.lead}</p>
        <div className="mt-10 grid gap-10">
          {page.sections.map((section, index) => (
            <section key={section.heading} aria-labelledby={`sec-${index}`} className="min-w-0">
              <h2 id={`sec-${index}`} className="text-2xl font-semibold">
                {section.heading}
              </h2>
              {section.body.map((p) => (
                <p key={p} className="mt-3 text-[17px] leading-relaxed">
                  {p}
                </p>
              ))}
              {section.list && (
                <ul className="mt-4 grid min-w-0 gap-2">
                  {section.list.map((item) => (
                    <li key={item} className="min-w-0">
                      <code className="block overflow-x-auto whitespace-pre rounded-lg bg-slate-950 px-4 py-3 text-base md:text-[15px] leading-relaxed text-slate-100">
                        {item}
                      </code>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>
        {page.checkpoint && (
          <aside className="mt-10 flex gap-4 rounded-xl border border-emerald-300 bg-emerald-50 p-6 text-emerald-950">
            <CircleCheck className="mt-1 size-6 shrink-0" aria-hidden="true" />
            <div>
              <p className="text-lg font-semibold">Check it works</p>
              <p className="mt-1 text-[17px]">{page.checkpoint}</p>
            </div>
          </aside>
        )}
        {page.next && (
          <div className="mt-10 border-t border-border pt-8">
            <p className="text-sm text-foreground/75">Next</p>
            <Link
              to={page.next.to}
              className="mt-2 inline-flex items-center gap-2 text-xl font-semibold text-primary hover:underline"
            >
              {page.next.label}
              <ArrowRight aria-hidden="true" />
            </Link>
          </div>
        )}
      </article>
    </div>
  );
}

function ArticleTemplate({ page }: { page: ArticlePage }) {
  return (
    <>
      <div className="border-b border-border bg-muted/40">
        <div className={`${CONTAINER} py-12 md:py-16`}>
          <div className="max-w-3xl">
            <Eyebrow>{page.eyebrow}</Eyebrow>
            <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-5xl">
              {page.title.split(" | ")[0]}
            </h1>
            <p className="mt-5 text-xl leading-relaxed text-foreground/80">{page.lead}</p>
            <p className="mt-4 text-sm text-foreground/75">
              {page.draft ? "Draft. Last revised " : "Page last reviewed "}
              {page.updated}
            </p>
          </div>
        </div>
      </div>
      <div className={`${CONTAINER} grid gap-12 py-12 md:py-16 lg:grid-cols-12`}>
        <div className="lg:col-span-8">
          {page.draft && (
            <p
              role="note"
              className="mb-10 rounded-xl border border-amber-300 bg-amber-50 p-4 text-[16px] text-amber-950"
            >
              Draft for review. Pending legal review. This text is not final until it has been
              reviewed and approved.
            </p>
          )}
          {page.pullquote && (
            <p className="mb-12 border-l-4 border-primary pl-6 text-xl font-semibold leading-snug tracking-tight text-foreground md:text-3xl">
              {page.pullquote}
            </p>
          )}
          <div className="grid gap-12">
            {page.sections.map((section) => (
              <section key={section.heading}>
                <h2 className="text-2xl font-semibold">{section.heading}</h2>
                {section.body.map((p) => (
                  <p key={p} className="mt-3 text-[17px] leading-relaxed text-foreground/85">
                    {p}
                  </p>
                ))}
                {section.list && (
                  <ul className="mt-4 grid list-disc gap-2 pl-6 text-[17px] leading-relaxed">
                    {section.list.map((item) => (
                      <li key={item} className="min-w-0">
                        {item}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            ))}
          </div>
        </div>
        <aside className="lg:col-span-4">
          <div className="grid gap-6 rounded-2xl border border-border bg-background p-6 lg:sticky lg:top-24">
            {page.draft ? (
              <div>
                <p className="text-xl font-semibold text-foreground">Questions about this page</p>
                <p className="mt-2 text-[16px] leading-relaxed text-foreground/85">
                  Contact us through the contact page with your question.
                </p>
                <div className="mt-4">
                  <SecondaryLink link={{ label: "Contact us", to: "/contact" }} />
                </div>
              </div>
            ) : (
              <div>
                <p className="text-xl font-semibold text-foreground">
                  Explore what we are building
                </p>
                <p className="mt-2 text-[16px] leading-relaxed text-foreground/85">
                  AI Chat is in active development. You can try the demo workspace today.
                </p>
                <div className="mt-4 flex flex-col gap-3">
                  <PrimaryLink link={PRIMARY_CTA} />
                  <SecondaryLink link={{ label: "Talk to the team", to: "/contact" }} />
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>
    </>
  );
}

function ListTemplate({ page }: { page: ListPage }) {
  const groups: Status[] = ["available", "active", "in-development", "planned", "vision"];
  return (
    <div className={`${CONTAINER} py-12 md:py-16`}>
      <div className="max-w-3xl">
        <Eyebrow>{page.eyebrow}</Eyebrow>
        <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-5xl">
          {page.title.split(" | ")[0]}
        </h1>
        <p className="mt-4 text-xl leading-relaxed text-foreground/75">{page.lead}</p>
      </div>
      <div className="mt-10 grid gap-10">
        {groups.map((status) => {
          const items = page.items.filter((item) => item.status === status);
          if (items.length === 0) return null;
          return (
            <section key={status} aria-labelledby={`g-${status}`}>
              <h2 id={`g-${status}`}>
                <StatusBadge status={status} />
              </h2>
              <ul className="mt-4 divide-y divide-border rounded-xl border border-border">
                {items.map((item) => (
                  <li key={item.id} className="grid gap-1 p-5 md:grid-cols-[16rem_1fr] md:gap-6">
                    <span className="text-lg font-semibold">{item.title}</span>
                    <span className="text-[17px] text-foreground/75">{item.text}</span>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function HubTemplate({ page }: { page: HubPage }) {
  return (
    <>
      <section className={SECTION_Y}>
        <div className={CONTAINER}>
          <div className="max-w-3xl">
            <Eyebrow>{page.eyebrow}</Eyebrow>
            <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-5xl">
              {page.title.split(" | ")[0]}
            </h1>
            <p className="mt-4 text-xl leading-relaxed text-foreground/75">{page.lead}</p>
            {page.path.startsWith("/docs") && (
              <p
                role="note"
                className="mt-6 rounded-xl border border-border bg-muted/50 p-4 text-[16px] text-foreground/85"
              >
                Documentation status: AI Chat is in active development. These guides describe the
                intended setup. Steps are not yet verified for production use.
              </p>
            )}
          </div>
          <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {page.cards.map((card) => (
              <li key={card.to + card.title}>
                <Link
                  to={card.to}
                  className="group flex h-full flex-col overflow-hidden rounded-2xl border border-border bg-background shadow-sm transition-shadow hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                >
                  {solutionImage(card.to) && (
                    <span className="block aspect-[4/3] overflow-hidden bg-slate-950">
                      <img
                        src={solutionImage(card.to)}
                        alt=""
                        aria-hidden="true"
                        width={1024}
                        height={768}
                        loading="lazy"
                        decoding="async"
                        className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
                      />
                    </span>
                  )}
                  <span className="flex flex-1 flex-col gap-3 p-6">
                    {card.status && <StatusBadge status={card.status} />}
                    <span className="text-xl font-semibold">{card.title}</span>
                    <span className="text-[17px] leading-relaxed text-foreground/75">
                      {card.text}
                    </span>
                    <span className="mt-auto inline-flex items-center gap-2 pt-2 font-medium text-primary">
                      Open
                      <ArrowRight
                        className="size-4 transition-transform group-hover:translate-x-1"
                        aria-hidden="true"
                      />
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>
      {page.path === "/products" && <ProductFamily id="family" />}
    </>
  );
}

function FormTemplate({ page }: { page: FormPage }) {
  const [checked, setChecked] = useState(false);
  const label: Record<FormPage["fields"][number], string> = {
    name: "Full name",
    email: "Work email",
    company: "Company (optional)",
    message: page.messageLabel,
  };
  return (
    <div className={`${CONTAINER} grid gap-12 py-12 md:py-16 lg:grid-cols-12`}>
      <div className="lg:col-span-5">
        <Eyebrow>{page.eyebrow}</Eyebrow>
        <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-5xl">
          {page.title.split(" | ")[0]}
        </h1>
        <p className="mt-4 text-xl leading-relaxed text-foreground/75">{page.lead}</p>
        <p
          role="note"
          className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4 text-[16px] text-amber-950"
        >
          {page.notice}
        </p>
      </div>
      <form
        className="grid gap-5 rounded-2xl border border-border p-6 md:p-8 lg:col-span-6 lg:col-start-7"
        onSubmit={(event) => {
          // Delivery is not connected. Nothing is sent, and the page says so.
          event.preventDefault();
          setChecked(true);
        }}
      >
        {page.fields.map((field) => {
          const id = `field-${field}`;
          const required = field !== "company";
          const common = {
            id,
            name: field,
            required,
            autoComplete:
              field === "name"
                ? "name"
                : field === "email"
                  ? "email"
                  : field === "company"
                    ? "organization"
                    : undefined,
            className:
              "rounded-lg border border-input bg-background px-4 py-3 text-[17px] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
          };
          return (
            <div key={field} className="grid gap-2">
              <label htmlFor={id} className="text-[16px] font-medium">
                {label[field]}
                {required && <span className="text-foreground/75"> (required)</span>}
              </label>
              {field === "message" ? (
                <textarea {...common} rows={5} />
              ) : (
                <input {...common} type={field === "email" ? "email" : "text"} />
              )}
            </div>
          );
        })}
        <Button type="submit" size="lg" className="h-12 justify-self-start px-6 text-base">
          {page.submitLabel}
          <ArrowRight aria-hidden="true" />
        </Button>
        {checked && (
          <p role="status" className="rounded-lg bg-muted p-4 text-[16px]">
            Your details look complete. Nothing was sent, because message delivery is not connected
            yet.
          </p>
        )}
      </form>
    </div>
  );
}

/** Renders any public page from its content record. */
export function SiteTemplate({ page }: { page: SitePage }) {
  let body: ReactNode;
  switch (page.kind) {
    case "landing":
      body = <LandingTemplate page={page} />;
      break;
    case "product":
      body = <ProductTemplate page={page} />;
      break;
    case "pricing":
      body = <PricingTemplate page={page} />;
      break;
    case "docs":
      body = <DocsTemplate page={page} />;
      break;
    case "article":
      body = <ArticleTemplate page={page} />;
      break;
    case "list":
      body = <ListTemplate page={page} />;
      break;
    case "hub":
      body = <HubTemplate page={page} />;
      break;
    case "form":
      body = <FormTemplate page={page} />;
      break;
  }
  return <SiteLayout>{body}</SiteLayout>;
}
