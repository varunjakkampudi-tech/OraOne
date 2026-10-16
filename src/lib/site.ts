// The public origin of the marketing site, used for canonical links, the sitemap and
// robots.txt. Override with VITE_SITE_URL for staging or previews.
export const SITE_URL = (import.meta.env["VITE_SITE_URL"] || "https://oraone.in").replace(
  /\/+$/,
  "",
);
