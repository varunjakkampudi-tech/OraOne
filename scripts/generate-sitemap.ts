/**
 * Writes public/sitemap.xml from the route inventory.
 *
 * A path is listed only when it is indexable (see isIndexablePath) and has no
 * dynamic segment, so private previews, auth screens and unapproved policies never
 * reach search engines. Run automatically before every build.
 *
 *   bun scripts/generate-sitemap.ts
 */
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { isIndexablePath } from "../src/lib/oraone";
import { SITE_URL } from "../src/lib/site";
import routeManifest from "../src/lib/route-manifest.json";

const paths = [...new Set(["/", ...routeManifest.map((route) => route.path)])]
  .filter((path) => !path.includes("$") && isIndexablePath(path))
  .sort((a, b) => a.localeCompare(b));

const urls = paths.map((path) => `  <url><loc>${SITE_URL}${path}</loc></url>`);
const xml = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  ...urls,
  "</urlset>",
  "",
].join("\n");

writeFileSync(resolve(import.meta.dirname, "../public/sitemap.xml"), xml, "utf-8");
console.log(`sitemap: ${paths.length} indexable pages for ${SITE_URL}`);
