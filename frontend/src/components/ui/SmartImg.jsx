import React, { useState } from "react";

/**
 * Inline SVG placeholder used when an image fails to load.
 * Encoded so it can also be used in the `loading="lazy"` poster slot.
 */
const PLACEHOLDER_SVG =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'>
      <defs>
        <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
          <stop offset='0%' stop-color='#EFF6FF'/>
          <stop offset='100%' stop-color='#E0E7FF'/>
        </linearGradient>
      </defs>
      <rect width='200' height='200' fill='url(#g)'/>
      <g fill='none' stroke='#94A3B8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
        <rect x='52' y='62' width='96' height='76' rx='10'/>
        <circle cx='80' cy='90' r='8' fill='#94A3B8' stroke='none'/>
        <path d='M60 130 l24-22 18 16 14-10 24 24'/>
      </g>
      <text x='100' y='168' text-anchor='middle' font-family='Inter, system-ui, sans-serif' font-size='10' fill='#64748B' font-weight='600' letter-spacing='1.5'>IMAGE UNAVAILABLE</text>
    </svg>`
  );

/**
 * SmartImg — drop-in <img> replacement.
 *
 *  • Defaults to `loading="lazy"` + `decoding="async"` so non-LCP images
 *    don't compete with the hero for bandwidth.
 *  • Pass `eager` to opt into eager loading (use for above-the-fold LCP
 *    images and the brand logo on the hero).
 *  • If the source fails to load, swaps to a tasteful inline SVG placeholder.
 */
export default function SmartImg({
  src,
  alt = "",
  eager = false,
  fetchPriority,
  onError,
  ...rest
}) {
  const [failed, setFailed] = useState(false);
  return (
    <img
      src={failed ? PLACEHOLDER_SVG : src}
      alt={alt}
      loading={eager ? "eager" : "lazy"}
      decoding="async"
      fetchPriority={fetchPriority || (eager ? "high" : "auto")}
      onError={(e) => {
        if (!failed) setFailed(true);
        if (onError) onError(e);
      }}
      {...rest}
    />
  );
}

export { PLACEHOLDER_SVG };
