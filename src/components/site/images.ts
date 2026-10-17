// Image paths for the public site. Generated art lives in public/media/generated; real
// product screens are captured from the running app into public/media.

const GEN = "/media/generated";
const SCREEN = "/media";

export const HERO_IMAGE: Record<string, string> = {
  "/": `${GEN}/hero-home.webp`,
  "/products/ai-chat": `${GEN}/hero-product.webp`,
  "/about": `${GEN}/about-mission.webp`,
};

/** Real product screens, used inside a browser frame. */
export const SCREENS = {
  inbox: `${SCREEN}/studio-inbox.jpg`,
  install: `${SCREEN}/studio-install.jpg`,
  assistant: `${SCREEN}/studio-assistant-editor.jpg`,
  knowledge: `${SCREEN}/studio-knowledge.jpg`,
  leads: `${SCREEN}/studio-leads.jpg`,
  demo: `${SCREEN}/widget-demo.webm`,
} as const;

const USE_CASE_IMAGE: Record<string, string> = {
  "Dental clinic": `${GEN}/use-dental.webp`,
  "Plumbing and heating": `${GEN}/use-plumbing.webp`,
  "Fitness studio": `${GEN}/use-fitness.webp`,
  "Online shop": `${GEN}/use-shop.webp`,
  "Accountancy or law practice": `${GEN}/use-legal.webp`,
  "Letting agency": `${GEN}/use-letting.webp`,
};

export function industryImage(industry: string): string | undefined {
  return USE_CASE_IMAGE[industry];
}

const SOLUTION_IMAGE: Record<string, string> = {
  "/solutions/customer-support": `${GEN}/solution-support.webp`,
  "/solutions/lead-generation": `${GEN}/solution-leads.webp`,
  "/solutions/sales": `${GEN}/solution-sales.webp`,
  "/solutions/small-business": `${GEN}/solution-small.webp`,
};

export function solutionImage(path: string): string | undefined {
  return SOLUTION_IMAGE[path];
}

/** Feature imagery for the home page feature rows, keyed by capability title. */
export const FEATURE_IMAGE: Record<string, string> = {
  "Website chat": `${GEN}/feature-widget.webp`,
  "Answers from your documents": `${GEN}/feature-knowledge.webp`,
  "Team inbox and leads": `${GEN}/feature-inbox.webp`,
  Leads: `${GEN}/feature-leads.webp`,
};
