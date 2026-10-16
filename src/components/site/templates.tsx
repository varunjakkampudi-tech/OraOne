import { useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import {
  ArrowRight,
  Check,
  CircleDashed,
  Clock,
  Sparkles,
  Hammer,
  CircleCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { DOCS_TREE, STATUS_LABEL } from "@/content/site/navigation";
import type {
  ArticlePage,
  Capability,
  DocsPage,
  FormPage,
  Faq,
  HubPage,
  LandingPage,
  Link as SiteLink,
  ListPage,
  PricingPage,
  ProductPage,
  SitePage,
  Status,
  Step,
} from "@/content/site/types";
import previewUrl from "@/assets/oraone-workspace-preview.png";
import { SiteLayout } from "./SiteLayout";

// One template per page kind. Every template uses the same spacing, type scale and
// status labels, so the public site reads as one product.

const STATUS_ICON: Record<Status, typeof CircleCheck> = {
  available: CircleCheck,
  beta: Sparkles,
  "in-development": Hammer,
  planned: Clock,
};

const STATUS_STYLE: Record<Status, string> = {
  available: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  beta: "bg-violet-50 text-violet-800 ring-violet-200",
  "in-development": "bg-amber-50 text-amber-900 ring-amber-300",
  planned: "bg-slate-100 text-slate-700 ring-slate-300",
};

export function StatusBadge({ status }: { status: Status }) {
  const Icon = STATUS_ICON[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-medium ring-1 ring-inset ${STATUS_STYLE[status]}`}
    >
      <Icon className="size-4" aria-hidden="true" />
      {STATUS_LABEL[status]}
    </span>
  );
}

function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="text-sm font-semibold uppercase tracking-wider text-primary">{children}</p>;
}

function Section({
  id,
  title,
  lead,
  children,
  tone = "default",
}: {
  id?: string;
  title?: string;
  lead?: string;
  children: ReactNode;
  tone?: "default" | "muted";
}) {
  return (
    <section
      id={id}
      className={`scroll-mt-24 px-5 py-16 md:px-8 md:py-24 ${tone === "muted" ? "bg-muted/40" : ""}`}
    >
      <div className="mx-auto max-w-6xl">
        {title && (
          <div className="max-w-2xl">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">{title}</h2>
            {lead && <p className="mt-4 text-lg text-muted-foreground">{lead}</p>}
          </div>
        )}
        <div className={title ? "mt-12" : ""}>{children}</div>
      </div>
    </section>
  );
}

function PrimaryLink({ link, size = "lg" }: { link: SiteLink; size?: "lg" | "default" }) {
  return (
    <Button asChild size={size} className="h-11 px-6 text-base">
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
      className={`h-11 px-6 text-base ${dark ? "border-white/40 bg-transparent text-white hover:bg-white/10 hover:text-white" : ""}`}
    >
      <Link to={link.to}>{link.label}</Link>
    </Button>
  );
}

function CapabilityGrid({ items }: { items: Capability[] }) {
  return (
    <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <li
          key={item.title}
          className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-6"
        >
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-xl font-semibold">{item.title}</h3>
          </div>
          <StatusBadge status={item.status} />
          <p className="text-[17px] leading-relaxed text-muted-foreground">{item.text}</p>
        </li>
      ))}
    </ul>
  );
}

function Steps({ steps }: { steps: Step[] }) {
  return (
    <ol className="grid gap-6 md:grid-cols-3">
      {steps.map((step, index) => (
        <li key={step.title} className="rounded-2xl border border-border bg-background p-6">
          <span className="grid size-10 place-items-center rounded-full bg-primary text-base font-semibold text-primary-foreground">
            {index + 1}
          </span>
          <h3 className="mt-5 text-xl font-semibold">{step.title}</h3>
          <p className="mt-2 text-[17px] leading-relaxed text-muted-foreground">{step.text}</p>
        </li>
      ))}
    </ol>
  );
}

function Faqs({ items }: { items: Faq[] }) {
  return (
    <div className="grid gap-3">
      {items.map((item) => (
        <details
          key={item.q}
          className="group rounded-xl border border-border bg-card px-5 py-4 open:shadow-sm"
        >
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-lg font-semibold [&::-webkit-details-marker]:hidden">
            {item.q}
            <span
              aria-hidden="true"
              className="text-2xl leading-none text-muted-foreground transition-transform group-open:rotate-45"
            >
              +
            </span>
          </summary>
          <p className="mt-3 text-[17px] leading-relaxed text-muted-foreground">{item.a}</p>
        </details>
      ))}
    </div>
  );
}

function CtaBand({ title, text, primary }: { title: string; text: string; primary: SiteLink }) {
  return (
    <section className="px-5 py-16 md:px-8 md:py-24">
      <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-8 rounded-3xl bg-slate-950 px-8 py-12 text-white md:flex-row md:items-center md:px-14">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">{title}</h2>
          <p className="mt-3 text-lg text-slate-300">{text}</p>
        </div>
        <Button
          asChild
          size="lg"
          className="h-11 bg-white px-6 text-base text-slate-950 hover:bg-slate-100"
        >
          <Link to={primary.to}>
            {primary.label}
            <ArrowRight aria-hidden="true" />
          </Link>
        </Button>
      </div>
    </section>
  );
}

function Hero({
  eyebrow,
  title,
  lead,
  primary,
  secondary,
  note,
  dark = false,
  image = true,
}: {
  eyebrow?: string;
  title: string;
  lead: string;
  primary: SiteLink;
  secondary: SiteLink | undefined;
  note?: string | undefined;
  dark?: boolean;
  image?: boolean;
}) {
  return (
    <section
      className={`px-5 py-16 md:px-8 md:py-24 ${dark ? "bg-slate-950 text-white" : "bg-background"}`}
    >
      <div
        className={`mx-auto grid max-w-6xl items-center gap-12 ${image ? "lg:grid-cols-2" : ""}`}
      >
        <div className="min-w-0">
          {eyebrow && (
            <p
              className={`text-sm font-semibold uppercase tracking-wider ${dark ? "text-sky-300" : "text-primary"}`}
            >
              {eyebrow}
            </p>
          )}
          <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight text-balance md:text-6xl">
            {title}
          </h1>
          <p
            className={`mt-6 max-w-xl text-lg leading-relaxed md:text-xl ${dark ? "text-slate-300" : "text-muted-foreground"}`}
          >
            {lead}
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <PrimaryLink link={primary} />
            {secondary && <SecondaryLink link={secondary} dark={dark} />}
          </div>
          {note && (
            <p
              className={`mt-6 max-w-xl text-[15px] ${dark ? "text-slate-400" : "text-muted-foreground"}`}
            >
              {note}
            </p>
          )}
        </div>
        {image && (
          <div className="min-w-0">
            <figure className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
              <img
                src={previewUrl}
                alt="The OraOne workspace showing the overview, inbox and leads with sample data"
                width={1280}
                height={900}
                loading="eager"
                decoding="async"
                className="block h-auto w-full"
              />
            </figure>
            <figcaption
              className={`mt-3 text-sm ${dark ? "text-slate-400" : "text-muted-foreground"}`}
            >
              Sample data shown. Your own information replaces it once you connect.
            </figcaption>
          </div>
        )}
      </div>
    </section>
  );
}

function LandingTemplate({ page }: { page: LandingPage }) {
  return (
    <>
      <Hero
        dark
        eyebrow={page.eyebrow}
        title={page.hero.title}
        lead={page.hero.lead}
        primary={page.hero.primary}
        secondary={page.hero.secondary}
        note={page.hero.note}
      />
      {page.statusLine.length > 0 && (
        <section
          aria-label="What is available"
          className="border-b border-border px-5 py-6 md:px-8"
        >
          <ul className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3">
            {page.statusLine.map((item) => (
              <li key={item.title} className="flex items-center gap-3">
                <span className="font-medium">{item.title}</span>
                <StatusBadge status={item.status} />
              </li>
            ))}
          </ul>
        </section>
      )}
      {page.outcomes.length > 0 && (
        <Section title="What changes for your business" tone="muted">
          <ul className="grid gap-6 md:grid-cols-3">
            {page.outcomes.map((item) => (
              <li key={item.title} className="rounded-2xl bg-background p-7 shadow-sm">
                <Check className="size-6 text-primary" aria-hidden="true" />
                <h3 className="mt-4 text-xl font-semibold">{item.title}</h3>
                <p className="mt-2 text-[17px] leading-relaxed text-muted-foreground">
                  {item.text}
                </p>
              </li>
            ))}
          </ul>
        </Section>
      )}
      {page.steps.length > 0 && (
        <Section
          id="how-it-works"
          title="Live in three steps"
          lead="No developer needed for the first version. Copy one line of code when you are ready."
        >
          <Steps steps={page.steps} />
        </Section>
      )}
      {page.capabilities.length > 0 && (
        <Section
          title="What you can use today"
          lead="Every item shows its real status. Items in development are not live yet."
        >
          <CapabilityGrid items={page.capabilities} />
        </Section>
      )}
      {page.faqs.length > 0 && (
        <Section title="Questions people ask" tone="muted">
          <div className="mx-auto max-w-3xl">
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
      />
      <Section title="The problem" tone="muted">
        <p className="max-w-3xl text-xl leading-relaxed">{page.problem}</p>
        <ul className="mt-8 grid gap-4 md:grid-cols-3">
          {page.outcomes.map((item) => (
            <li
              key={item}
              className="flex items-start gap-3 rounded-2xl bg-background p-6 shadow-sm"
            >
              <Check className="mt-1 size-5 shrink-0 text-primary" aria-hidden="true" />
              <span className="text-lg">{item}</span>
            </li>
          ))}
        </ul>
      </Section>
      {page.steps.length > 0 && (
        <Section title="How to get started">
          <Steps steps={page.steps} />
        </Section>
      )}
      {page.capabilities.length > 0 && (
        <Section title="Capabilities" lead="The status of each capability is shown on its card.">
          <CapabilityGrid items={page.capabilities} />
        </Section>
      )}
      {page.faqs.length > 0 && (
        <Section title="Questions" tone="muted">
          <div className="mx-auto max-w-3xl">
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
      <section className="px-5 py-16 md:px-8 md:py-24">
        <div className="mx-auto max-w-6xl">
          <Eyebrow>{page.eyebrow}</Eyebrow>
          <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-6xl">
            Simple access while we build
          </h1>
          <p className="mt-6 max-w-2xl text-xl text-muted-foreground">{page.lead}</p>
          <div className="mt-12 grid gap-6 md:grid-cols-1 lg:max-w-3xl">
            {page.plans.map((plan) => (
              <article
                key={plan.name}
                className="rounded-3xl border border-primary/30 bg-card p-8 shadow-lg md:p-10"
              >
                <h2 className="text-2xl font-semibold">{plan.name}</h2>
                <p className="mt-2 text-lg text-muted-foreground">{plan.summary}</p>
                <p className="mt-6 text-5xl font-bold">{plan.price}</p>
                <ul className="mt-8 grid gap-3">
                  {plan.items.map((item) => (
                    <li key={item} className="flex items-start gap-3 text-lg">
                      <Check className="mt-1 size-5 shrink-0 text-primary" aria-hidden="true" />
                      {item}
                    </li>
                  ))}
                </ul>
                <div className="mt-10">
                  <PrimaryLink link={plan.cta} />
                </div>
              </article>
            ))}
          </div>
          <ul className="mt-10 grid gap-3 text-lg text-muted-foreground lg:max-w-3xl">
            {page.notes.map((note) => (
              <li key={note} className="flex items-start gap-3">
                <CircleDashed className="mt-1 size-5 shrink-0" aria-hidden="true" />
                {note}
              </li>
            ))}
          </ul>
        </div>
      </section>
      <Section title="Pricing questions" tone="muted">
        <div className="mx-auto max-w-3xl">
          <Faqs items={page.faqs} />
        </div>
      </Section>
    </>
  );
}

function DocsTemplate({ page }: { page: DocsPage }) {
  return (
    <div className="mx-auto grid max-w-7xl gap-10 px-5 py-12 md:px-8 lg:grid-cols-[16rem_minmax(0,1fr)] lg:py-16">
      <aside aria-label="Documentation" className="lg:sticky lg:top-24 lg:self-start">
        <nav className="grid gap-6">
          {DOCS_TREE.map((group) => (
            <div key={group.group}>
              <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {group.group}
              </p>
              <ul className="mt-2 grid gap-1">
                {group.links.map((item) => (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      aria-current={item.to === page.path ? "page" : undefined}
                      className={`block rounded-lg px-3 py-2 text-[15px] ${item.to === page.path ? "bg-accent font-semibold text-accent-foreground" : "hover:bg-muted"}`}
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
        <p className="mt-5 text-xl leading-relaxed text-muted-foreground">{page.lead}</p>
        <div className="mt-12 grid gap-12">
          {page.sections.map((section, index) => (
            <section key={section.heading} aria-labelledby={`sec-${index}`}>
              <h2 id={`sec-${index}`} className="text-2xl font-semibold">
                {section.heading}
              </h2>
              {section.body.map((p) => (
                <p key={p} className="mt-3 text-[17px] leading-relaxed">
                  {p}
                </p>
              ))}
              {section.list && (
                <ul className="mt-4 grid gap-2">
                  {section.list.map((item) => (
                    <li key={item}>
                      <code className="block overflow-x-auto whitespace-pre rounded-lg bg-slate-950 px-4 py-3 text-[15px] leading-relaxed text-slate-100">
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
          <aside className="mt-12 flex gap-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
            <CircleCheck className="mt-1 size-6 shrink-0 text-emerald-700" aria-hidden="true" />
            <div>
              <p className="text-lg font-semibold text-emerald-900">Check it works</p>
              <p className="mt-1 text-[17px] text-emerald-900">{page.checkpoint}</p>
            </div>
          </aside>
        )}
        {page.next && (
          <div className="mt-12 border-t border-border pt-8">
            <p className="text-sm text-muted-foreground">Next</p>
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
    <div className="mx-auto max-w-3xl px-5 py-12 md:px-8 md:py-20">
      <Eyebrow>{page.eyebrow}</Eyebrow>
      <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-5xl">
        {page.title.split(" | ")[0]}
      </h1>
      <p className="mt-5 text-xl leading-relaxed text-muted-foreground">{page.lead}</p>
      <p className="mt-4 text-sm text-muted-foreground">Last updated {page.updated}</p>
      {page.draft && (
        <p
          role="note"
          className="mt-8 rounded-xl border border-amber-300 bg-amber-50 p-4 text-[16px] text-amber-950"
        >
          Draft for review. This text is not final until it has been reviewed and approved.
        </p>
      )}
      <nav aria-label="On this page" className="mt-10 rounded-2xl bg-muted/50 p-6">
        <p className="font-semibold">On this page</p>
        <ol className="mt-3 grid list-decimal gap-2 pl-5 text-[16px]">
          {page.sections.map((section, index) => (
            <li key={section.heading}>
              <a href={`#s-${index}`} className="text-primary hover:underline">
                {section.heading}
              </a>
            </li>
          ))}
        </ol>
      </nav>
      <div className="mt-12 grid gap-12">
        {page.sections.map((section, index) => (
          <section key={section.heading} id={`s-${index}`} className="scroll-mt-24">
            <h2 className="text-2xl font-semibold">{section.heading}</h2>
            {section.body.map((p) => (
              <p key={p} className="mt-3 text-[17px] leading-relaxed">
                {p}
              </p>
            ))}
            {section.list && (
              <ul className="mt-4 grid list-disc gap-2 pl-6 text-[17px] leading-relaxed">
                {section.list.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

function ListTemplate({ page }: { page: ListPage }) {
  const groups: Status[] = ["available", "beta", "in-development", "planned"];
  return (
    <div className="mx-auto max-w-5xl px-5 py-12 md:px-8 md:py-20">
      <Eyebrow>{page.eyebrow}</Eyebrow>
      <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-5xl">
        {page.title.split(" | ")[0]}
      </h1>
      <p className="mt-5 max-w-3xl text-xl leading-relaxed text-muted-foreground">{page.lead}</p>
      <div className="mt-12 grid gap-10">
        {groups.map((status) => {
          const items = page.items.filter((item) => item.status === status);
          if (items.length === 0) return null;
          return (
            <section key={status} aria-labelledby={`g-${status}`}>
              <h2 id={`g-${status}`} className="flex items-center gap-3 text-2xl font-semibold">
                <StatusBadge status={status} />
              </h2>
              <ul className="mt-5 divide-y divide-border rounded-2xl border border-border bg-card">
                {items.map((item) => (
                  <li key={item.id} className="grid gap-1 p-5 md:grid-cols-[14rem_1fr] md:gap-6">
                    <span className="text-lg font-semibold">{item.title}</span>
                    <span className="text-[17px] text-muted-foreground">{item.text}</span>
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
      <section className="px-5 py-16 md:px-8 md:py-20">
        <div className="mx-auto max-w-6xl">
          <Eyebrow>{page.eyebrow}</Eyebrow>
          <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-6xl">
            {page.title.split(" | ")[0]}
          </h1>
          <p className="mt-6 max-w-3xl text-xl leading-relaxed text-muted-foreground">
            {page.lead}
          </p>
        </div>
      </section>
      <section className="px-5 pb-20 md:px-8">
        <ul className="mx-auto grid max-w-6xl gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {page.cards.map((card) => (
            <li key={card.to + card.title}>
              <Link
                to={card.to}
                className="group flex h-full flex-col gap-3 rounded-2xl border border-border bg-card p-7 transition-shadow hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                {card.status && <StatusBadge status={card.status} />}
                <span className="text-xl font-semibold">{card.title}</span>
                <span className="text-[17px] leading-relaxed text-muted-foreground">
                  {card.text}
                </span>
                <span className="mt-auto inline-flex items-center gap-2 pt-2 font-medium text-primary">
                  Open
                  <ArrowRight
                    className="size-4 transition-transform group-hover:translate-x-1"
                    aria-hidden="true"
                  />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
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
    <div className="mx-auto grid max-w-6xl gap-12 px-5 py-12 md:px-8 md:py-20 lg:grid-cols-[1fr_1.1fr]">
      <div>
        <Eyebrow>{page.eyebrow}</Eyebrow>
        <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-5xl">
          {page.title.split(" | ")[0]}
        </h1>
        <p className="mt-5 text-xl leading-relaxed text-muted-foreground">{page.lead}</p>
        <p
          role="note"
          className="mt-8 rounded-xl border border-amber-300 bg-amber-50 p-4 text-[16px] text-amber-950"
        >
          {page.notice}
        </p>
      </div>
      <form
        className="grid gap-5 rounded-3xl border border-border bg-card p-6 md:p-8"
        onSubmit={(event) => {
          // Delivery is not connected. Nothing is sent, and the form says so instead of
          // claiming a message was received.
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
                {required && <span className="text-muted-foreground"> (required)</span>}
              </label>
              {field === "message" ? (
                <textarea {...common} rows={5} />
              ) : (
                <input {...common} type={field === "email" ? "email" : "text"} />
              )}
            </div>
          );
        })}
        <Button type="submit" size="lg" className="h-11 justify-self-start px-6 text-base">
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
