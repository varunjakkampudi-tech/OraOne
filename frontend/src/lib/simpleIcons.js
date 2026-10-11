const SIMPLE_ICON_ALIASES = {
  api: "openapiinitiative",
  facebook: "facebook",
  github: "github",
  gmail: "gmail",
  googlecalendar: "googlecalendar",
  "google-calendar": "googlecalendar",
  hubspot: "hubspot",
  instagram: "instagram",
  linkedin: "linkedin",
  microsoftoutlook: "microsoftoutlook",
  microsoftteams: "microsoftteams",
  notion: "notion",
  openapi: "openapiinitiative",
  outlook: "microsoftoutlook",
  pipedrive: "pipedrive",
  salesforce: "salesforce",
  shopify: "shopify",
  slack: "slack",
  stripe: "stripe",
  teams: "microsoftteams",
  twitter: "x",
  webhook: "webhooks",
  webhooks: "webhooks",
  whatsapp: "whatsapp",
  x: "x",
  youtube: "youtube",
  zendesk: "zendesk",
  zoho: "zoho",
  "zoho-crm": "zoho",
};

// A few high-value brands are unavailable on cdn.simpleicons.org.
// Use trusted logo hosts for those so cards don't fall back to placeholders.
const SIMPLE_ICON_FALLBACK_URLS = {
  linkedin: "https://cdn.worldvectorlogo.com/logos/linkedin-icon-3.svg",
  pipedrive: "https://cdn.worldvectorlogo.com/logos/pipedrive.svg",
  // Slack + Salesforce slugs were removed from Simple Icons (trademark) -> use official colored marks
  slack: "https://upload.wikimedia.org/wikipedia/commons/d/d5/Slack_icon_2019.svg",
  salesforce: "https://upload.wikimedia.org/wikipedia/commons/f/f9/Salesforce.com_logo.svg",
  gmail: "https://cdn.simpleicons.org/gmail/EA4335",
  googlecalendar: "https://cdn.simpleicons.org/googlecalendar/4285F4",
  hubspot: "https://cdn.simpleicons.org/hubspot/FF7A59",
  teams: "https://cdn.worldvectorlogo.com/logos/microsoft-teams-1.svg",
  microsoftteams: "https://cdn.worldvectorlogo.com/logos/microsoft-teams-1.svg",
  outlook: "https://cdn.worldvectorlogo.com/logos/microsoft-outlook-2013-logo.svg",
  microsoftoutlook: "https://cdn.worldvectorlogo.com/logos/microsoft-outlook-2013-logo.svg",
  webhook: "https://cdn.simpleicons.org/zapier",
  webhooks: "https://cdn.simpleicons.org/zapier",
};

export function resolveSimpleIconSlug(slug) {
  if (!slug) return null;
  const normalized = String(slug).trim().toLowerCase();
  return SIMPLE_ICON_ALIASES[normalized] || normalized.replace(/[^a-z0-9]/g, "");
}

export function normalizeSimpleIconColor(color) {
  if (!color || color === "currentColor") return null;
  return color.replace(/^#/, "");
}

export function getSimpleIconUrl(slug, color) {
  const resolvedSlug = resolveSimpleIconSlug(slug);
  if (!resolvedSlug) return null;

  if (SIMPLE_ICON_FALLBACK_URLS[resolvedSlug]) {
    return SIMPLE_ICON_FALLBACK_URLS[resolvedSlug];
  }

  const resolvedColor = normalizeSimpleIconColor(color);
  return resolvedColor
    ? `https://cdn.simpleicons.org/${resolvedSlug}/${resolvedColor}`
    : `https://cdn.simpleicons.org/${resolvedSlug}`;
}

export function formatSimpleIconTitle(slug) {
  if (!slug) return "Brand icon";
  return String(slug)
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}