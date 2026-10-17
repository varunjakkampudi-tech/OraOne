// Types for the public site content. Every page is described by data here and rendered by
// one of the templates in components/site, so copy and layout stay separate.

/** How far a capability has got. Shown as a labelled badge, never by colour alone. */
/** available: works today. active: Product 1 is in active development. in-development: not live yet. planned: on the roadmap. vision: long-term. */
export type Status = "available" | "active" | "beta" | "in-development" | "planned" | "vision";

export type Capability = { title: string; text: string; status: Status };

export type Step = { title: string; text: string };

export type Faq = { q: string; a: string };

export type UseCase = { industry: string; problem: string; assistant: string; team: string };

export type Link = { label: string; to: string };

export type Hero = {
  title: string;
  lead: string;
  primary: Link;
  secondary?: Link;
  note?: string;
};

export type Section = { heading: string; body: string[]; list?: string[] };

export type Plan = {
  name: string;
  price: string;
  summary: string;
  items: string[];
  cta: Link;
};

type Base = { path: string; title: string };

export type LandingPage = Base & {
  kind: "landing";
  eyebrow: string;
  hero: Hero;
  statusLine: Capability[];
  outcomes: { title: string; text: string }[];
  steps: Step[];
  capabilities: Capability[];
  useCases: UseCase[];
  faqs: Faq[];
  cta: { title: string; text: string; primary: Link };
  showcase?: boolean;
};

export type ProductPage = Base & {
  kind: "product";
  eyebrow: string;
  hero: Hero;
  problem: string;
  outcomes: string[];
  capabilities: Capability[];
  useCases: UseCase[];
  steps: Step[];
  faqs: Faq[];
  cta: { title: string; text: string; primary: Link };
  showcase?: boolean;
};

export type PricingPage = Base & {
  kind: "pricing";
  eyebrow: string;
  lead: string;
  plans: Plan[];
  notes: string[];
  faqs: Faq[];
};

export type DocsPage = Base & {
  kind: "docs";
  group: string;
  lead: string;
  sections: Section[];
  checkpoint?: string;
  next?: Link;
};

export type ArticlePage = Base & {
  kind: "article";
  eyebrow: string;
  lead: string;
  updated: string;
  draft?: boolean;
  pullquote?: string;
  sections: Section[];
};

export type ListPage = Base & {
  kind: "list";
  eyebrow: string;
  lead: string;
  items: (Capability & { id: string })[];
};

export type HubPage = Base & {
  kind: "hub";
  eyebrow: string;
  lead: string;
  cards: { title: string; text: string; to: string; status?: Status }[];
};

export type FormPage = Base & {
  kind: "form";
  eyebrow: string;
  lead: string;
  fields: ("name" | "email" | "company" | "message")[];
  messageLabel: string;
  submitLabel: string;
  notice: string;
};

export type SitePage =
  LandingPage | ProductPage | PricingPage | DocsPage | ArticlePage | ListPage | HubPage | FormPage;
