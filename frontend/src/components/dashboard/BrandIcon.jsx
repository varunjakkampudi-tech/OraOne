import React from "react";
import {
  siGmail,
  siGoogledrive,
  siDropbox,
  siNotion,
  siConfluence,
  siGitbook,
  siGithub,
  siGitlab,
  siJira,
  siHubspot,
  siZendesk,
  siWhatsapp,
} from "simple-icons";

/* Brand logos (simple-icons) for integration/channel providers.
   Providers without a trademark-clear icon (slack, salesforce, microsoft*)
   fall back to the lucide glyph the caller already has. */
const BRAND = {
  gmail: siGmail,
  google_drive: siGoogledrive,
  dropbox: siDropbox,
  notion: siNotion,
  confluence: siConfluence,
  gitbook: siGitbook,
  github: siGithub,
  gitlab: siGitlab,
  jira: siJira,
  hubspot: siHubspot,
  zendesk: siZendesk,
  whatsapp: siWhatsapp,
};

export function hasBrandIcon(provider) {
  return !!BRAND[provider];
}

export function brandHex(provider) {
  const icon = BRAND[provider];
  return icon ? `#${icon.hex}` : null;
}

export function BrandIcon({ provider, size = 20, color }) {
  const icon = BRAND[provider];
  if (!icon) return null;
  return (
    <svg
      role="img"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill={color || `#${icon.hex}`}
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path d={icon.path} />
    </svg>
  );
}
