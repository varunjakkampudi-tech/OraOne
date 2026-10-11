import React from "react";
import SmartImg from "@/components/ui/SmartImg";
import { formatSimpleIconTitle, getSimpleIconUrl } from "@/lib/simpleIcons";

/**
 * SimpleIcon — render any brand icon from Simple Icons using the official CDN.
 *
 * Usage:
 *   <SimpleIcon slug="github" size={20} />
 *   <SimpleIcon slug="whatsapp" size={28} color="#25D366" />
 *   <SimpleIcon slug="googlecalendar" />
 *   <SimpleIcon slug="x" size={20} color="#FFFFFF" />
 *
 * Props:
 *   slug          (string, required) — Simple Icons slug, e.g. "github", "x".
 *   size          (number) — width & height in px. Default 20.
 *   color         (string) — hex color to tint the icon, e.g. "#FFFFFF".
 *   useBrandColor (bool)   — if true, uses the brand's official Simple Icons color.
 *   title         (string) — accessible label; defaults to a titleized slug.
 *   className     (string) — additional CSS classes.
 *   ...rest               — forwarded to the underlying <img> element.
 */
export default function SimpleIcon({
  slug,
  size = 20,
  color,
  useBrandColor = false,
  title,
  className = "",
  ...rest
}) {
  const src = getSimpleIconUrl(slug, useBrandColor ? null : color);

  if (!src) {
    if (process.env.NODE_ENV !== "production") {
      console.warn(`[SimpleIcon] No icon URL could be generated for slug "${slug}".`);
    }
    return null;
  }

  return (
    <SmartImg
      src={src}
      alt={title || formatSimpleIconTitle(slug)}
      width={size}
      height={size}
      aria-label={title || formatSimpleIconTitle(slug)}
      className={className}
      {...rest}
    />
  );
}