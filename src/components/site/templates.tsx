import { useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import { ArrowRight, Check, CircleCheck, Clock, Hammer, Sparkles, Waypoints } from "lucide-react";
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
import { CONTAINER, SECTION_Y } from "./layout";
import { capabilityIcon, industryIcon, productIcon, stepIcon } from "./icons";
import { IconTile } from "./IconTile";

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
            {lead && (
              <p className="mt-3 text-[17px] leading-relaxed text-muted-foreground">{lead}</p>
            )}
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
  const muted = dark ? "text-slate-300" : "text-muted-foreground";
  return (
    <figure
      role="img"
      aria-label="Illustration: a visitor's question goes to the OraOne assistant, which answers from your documents or passes it to your team"
      className={`rounded-2xl border p-6 md:p-8 ${dark ? "border-white/10 bg-slate-900" : "border-border bg-muted/40"}`}
    >
      <div className="grid gap-4">
        <div className={`rounded-xl border p-4 ${node}`}>
          <p className="font-semibold">Visitor asks a question</p>
          <p className={`mt-1 text-[15px] ${muted}`}>On your website, at any hour</p>
        </div>
        <div className="flex justify-center" aria-hidden="true">
          <div className={`h-6 w-px ${dark ? "bg-white/30" : "bg-slate-300"}`} />
        </div>
        <div
          className={`rounded-xl border-2 p-4 ${dark ? "border-sky-400 bg-sky-400/10" : "border-primary bg-primary/5"}`}
        >
          <p className="font-semibold">OraOne assistant</p>
          <p className={`mt-1 text-[15px] ${muted}`}>
            Answers from your documents and cites its sources
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className={`rounded-xl border p-4 ${node}`}>
            <p className="font-semibold">Answered</p>
            <p className={`mt-1 text-[15px] ${muted}`}>The visitor gets a clear reply</p>
          </div>
          <div className={`rounded-xl border p-4 ${node}`}>
            <p className="font-semibold">Handed to your team</p>
            <p className={`mt-1 text-[15px] ${muted}`}>Lead and history in the inbox</p>
          </div>
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
  dark = false,
  visual = true,
}: {
  eyebrow?: string;
  title: string;
  lead: string;
  primary: SiteLink;
  secondary?: SiteLink | undefined;
  note?: string | undefined;
  dark?: boolean;
  visual?: boolean;
}) {
  return (
    <section
      className={`relative isolate overflow-hidden ${SECTION_Y} ${dark ? "bg-slate-950 text-white" : ""}`}
    >
      {dark && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 -top-40 -z-10 h-[32rem] bg-[radial-gradient(60%_50%_at_50%_0%,rgba(29,78,216,0.35),transparent)]"
        />
      )}
      <div className={`${CONTAINER} grid items-center gap-12 ${visual ? "lg:grid-cols-12" : ""}`}>
        <div className={visual ? "lg:col-span-6" : "max-w-3xl"}>
          {eyebrow && <Eyebrow dark={dark}>{eyebrow}</Eyebrow>}
          <h1 className="mt-4 text-4xl font-bold leading-[1.1] tracking-tight text-balance md:text-5xl lg:text-[56px]">
            {title}
          </h1>
          <p
            className={`mt-5 max-w-xl text-lg leading-relaxed md:text-xl ${dark ? "text-slate-300" : "text-muted-foreground"}`}
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
        {visual && (
          <div className="lg:col-span-6">
            <FlowDiagram dark={dark} />
          </div>
        )}
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
          <p className="text-[17px] leading-relaxed text-muted-foreground">{item.text}</p>
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
          className="flex flex-col gap-4 rounded-xl border border-border bg-background p-6 shadow-sm"
        >
          <div className="flex items-center gap-3">
            <IconTile icon={stepIcon(index)} tone="muted" />
            <span className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Step {index + 1}
            </span>
          </div>
          <h3 className="text-xl font-semibold">{step.title}</h3>
          <p className="text-[17px] leading-relaxed text-muted-foreground">{step.text}</p>
        </li>
      ))}
    </ol>
  );
}

function UseCaseGrid({ items }: { items: UseCase[] }) {
  return (
    <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <li
          key={item.industry}
          className="flex flex-col gap-4 rounded-xl border border-border bg-background p-6 shadow-sm transition-shadow hover:shadow-md"
        >
          <div className="flex items-center gap-3">
            <IconTile icon={industryIcon(item.industry)} />
            <p className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              {item.industry}
            </p>
          </div>
          <h3 className="text-xl font-semibold">{item.problem}</h3>
          <p className="text-[17px] leading-relaxed text-muted-foreground">
            <span className="font-medium text-foreground">The assistant </span>
            {item.assistant}
          </p>
          <p className="text-[17px] leading-relaxed text-muted-foreground">
            <span className="font-medium text-foreground">Your team </span>
            {item.team}
          </p>
        </li>
      ))}
    </ul>
  );
}

function Faqs({ items }: { items: Faq[] }) {
  return (
    <div className="grid gap-3">
      {items.map((item) => (
        <details key={item.q} className="group rounded-xl border border-border px-5 py-4">
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

/** The complete OraOne family, one row per product, with an honest status on each. */
export function ProductFamily({ id = "products" }: { id?: string }) {
  return (
    <section
      id={id}
      className={`scroll-mt-20 ${SECTION_Y} bg-muted/40`}
      aria-labelledby={`${id}-heading`}
    >
      <div className={CONTAINER}>
        <div className="max-w-2xl">
          <h2 id={`${id}-heading`} className="text-3xl font-bold tracking-tight md:text-4xl">
            The OraOne product family
          </h2>
          <p className="mt-3 text-[17px] leading-relaxed text-muted-foreground">
            AI Chat is in active development. Every other product is planned or a long-term vision,
            and is labelled as such.
          </p>
        </div>
        <ol className="mt-8 divide-y divide-border rounded-xl border border-border bg-background">
          {PORTFOLIO.map((product) => (
            <li
              key={product.id}
              className="grid gap-3 p-5 md:grid-cols-[2.75rem_18rem_1fr_auto] md:items-center md:gap-6"
            >
              <IconTile
                icon={productIcon(product.id)}
                tone={product.status === "active" ? "brand" : "muted"}
              />
              <Link
                to={product.id === 1 ? "/products/ai-chat" : "/roadmap"}
                className="text-lg font-semibold hover:text-primary hover:underline"
              >
                {product.name}
              </Link>
              <span className="text-[17px] text-muted-foreground">{product.summary}</span>
              <span className="md:justify-self-end">
                <StatusBadge status={product.status} />
              </span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function CtaBand({ title, text, primary }: { title: string; text: string; primary: SiteLink }) {
  return (
    <section className={SECTION_Y}>
      <div className={CONTAINER}>
        <div className="flex flex-col items-start justify-between gap-6 rounded-2xl bg-slate-950 p-8 text-white md:flex-row md:items-center md:p-12">
          <div className="max-w-2xl">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">{title}</h2>
            <p className="mt-3 text-lg text-slate-300">{text}</p>
          </div>
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
        </div>
      </div>
    </section>
  );
}

/** Real screens from the product and the widget demo. Video is opt-in: nothing loads until it is played. */
function Showcase() {
  return (
    <Section
      title="See it in the product"
      lead="Real screens from AI Chat, with example information. The video shows a visitor asking questions on a website."
    >
      <div className="grid gap-8 lg:grid-cols-12">
        <figure className="lg:col-span-7">
          <img
            src="/media/studio-inbox.jpg"
            alt="The team inbox listing each conversation with its assistant and time"
            width={1280}
            height={800}
            loading="lazy"
            decoding="async"
            className="w-full rounded-xl border border-border"
          />
          <figcaption className="mt-3 text-[15px] text-muted-foreground">
            Team inbox: every conversation, with its history.
          </figcaption>
        </figure>
        <figure className="lg:col-span-5">
          <img
            src="/media/studio-install.jpg"
            alt="The install screen showing the script tag to copy into a website"
            width={1280}
            height={800}
            loading="lazy"
            decoding="async"
            className="w-full rounded-xl border border-border"
          />
          <figcaption className="mt-3 text-[15px] text-muted-foreground">
            Install: one line of code for your site.
          </figcaption>
        </figure>
        <figure className="lg:col-span-12">
          <video
            controls
            preload="none"
            playsInline
            poster="/media/studio-inbox.jpg"
            aria-label="Widget demo: a visitor asks about opening hours and booking on an example clinic website"
            className="w-full rounded-xl border border-border bg-slate-950"
          >
            <source src="/media/widget-demo.webm" type="video/webm" />
          </video>
          <figcaption className="mt-3 text-[15px] text-muted-foreground">
            A visitor chats on a website. Answers come from the example information in the knowledge
            base.
          </figcaption>
        </figure>
      </div>
    </Section>
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
      {page.showcase && <Showcase />}
      {page.steps.length > 0 && (
        <Section
          title="How it works"
          lead="Three steps. A developer is only needed if you add the chat with code."
        >
          <Steps steps={page.steps} />
        </Section>
      )}
      {page.capabilities.length > 0 && (
        <Section title="What you can use" lead="Each item shows its real status." muted>
          <CapabilityGrid items={page.capabilities} />
        </Section>
      )}
      {page.useCases.length > 0 && (
        <Section
          title="Where it helps"
          lead="Illustrative examples of how a business might use an assistant. They describe the intended workflow, not real customers or results."
        >
          <UseCaseGrid items={page.useCases} />
        </Section>
      )}
      <ProductFamily />
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
            <p className="mt-4 text-lg leading-relaxed text-muted-foreground">{page.lead}</p>
          </div>
          <div className="mt-8 grid gap-4 lg:max-w-3xl">
            {page.plans.map((plan) => (
              <article key={plan.name} className="rounded-2xl border border-primary/40 p-6 md:p-8">
                <div className="flex flex-wrap items-baseline justify-between gap-4">
                  <h2 className="text-2xl font-semibold">{plan.name}</h2>
                  <p className="text-4xl font-bold">{plan.price}</p>
                </div>
                <p className="mt-2 text-[17px] text-muted-foreground">{plan.summary}</p>
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
          <ul className="mt-8 grid gap-2 text-[17px] text-muted-foreground lg:max-w-3xl">
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
    <div className={`${CONTAINER} grid gap-10 py-12 lg:grid-cols-[14rem_minmax(0,1fr)] lg:py-16`}>
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
        <p className="mt-4 text-xl leading-relaxed text-muted-foreground">{page.lead}</p>
        <div className="mt-10 grid gap-10">
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
    <div className={`${CONTAINER} py-12 md:py-16`}>
      <div className="max-w-3xl">
        <Eyebrow>{page.eyebrow}</Eyebrow>
        <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-5xl">
          {page.title.split(" | ")[0]}
        </h1>
        <p className="mt-4 text-xl leading-relaxed text-muted-foreground">{page.lead}</p>
        <p className="mt-3 text-sm text-muted-foreground">Last updated {page.updated}</p>
        {page.draft && (
          <p
            role="note"
            className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-4 text-[16px] text-amber-950"
          >
            Draft for review. This text is not final until it has been reviewed and approved.
          </p>
        )}
        <div className="mt-10 grid gap-10">
          {page.sections.map((section) => (
            <section key={section.heading}>
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
    </div>
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
        <p className="mt-4 text-xl leading-relaxed text-muted-foreground">{page.lead}</p>
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
      <section className={SECTION_Y}>
        <div className={CONTAINER}>
          <div className="max-w-3xl">
            <Eyebrow>{page.eyebrow}</Eyebrow>
            <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-5xl">
              {page.title.split(" | ")[0]}
            </h1>
            <p className="mt-4 text-xl leading-relaxed text-muted-foreground">{page.lead}</p>
          </div>
          <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {page.cards.map((card) => (
              <li key={card.to + card.title}>
                <Link
                  to={card.to}
                  className="group flex h-full flex-col gap-3 rounded-xl border border-border p-6 transition-colors hover:border-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
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
        </div>
      </section>
      <ProductFamily id="family" />
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
        <p className="mt-4 text-xl leading-relaxed text-muted-foreground">{page.lead}</p>
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
