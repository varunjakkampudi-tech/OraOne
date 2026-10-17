// Image paths for the public site. Generated art lives in public/media/generated; real
// product screens are captured from the running app into public/media.

const GEN = "/media/generated";
const SCREEN = "/media";

/** Real product screens, used inside a browser frame. */
export const SCREENS = {
  inbox: `${SCREEN}/studio-inbox.jpg`,
  install: `${SCREEN}/studio-install.jpg`,
  assistant: `${SCREEN}/studio-assistant-editor.jpg`,
  knowledge: `${SCREEN}/studio-knowledge.jpg`,
  leads: `${SCREEN}/studio-leads.jpg`,
} as const;

const SOLUTION_IMAGE: Record<string, string> = {
  "/solutions/customer-support": `${GEN}/solution-support.webp`,
  "/solutions/lead-generation": `${GEN}/solution-leads.webp`,
  "/solutions/sales": `${GEN}/solution-sales.webp`,
  "/solutions/small-business": `${GEN}/solution-small.webp`,
};

export function solutionImage(path: string): string | undefined {
  return SOLUTION_IMAGE[path];
}
