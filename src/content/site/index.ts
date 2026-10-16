import { docsPages } from "./docs";
import { legalPages } from "./legal";
import { marketingPages } from "./marketing";
import type { SitePage } from "./types";

export type { SitePage } from "./types";
export * from "./navigation";

// Every public page, keyed by its path. Route files look their page up here.
export const SITE_PAGES: Record<string, SitePage> = Object.fromEntries(
  [...marketingPages, ...docsPages, ...legalPages].map((page) => [page.path, page]),
);

export function sitePage(path: string): SitePage {
  const page = SITE_PAGES[path];
  if (!page) throw new Error(`No public page content for ${path}`);
  return page;
}
