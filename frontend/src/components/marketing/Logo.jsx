import React from "react";

/* =========================================================================
   OraOne brand logo — "Orbit": one central AI core with a conversation node
   orbiting a continuous (always-on) ring, in the brand blue -> cyan gradient.

   The mark encodes the product vision literally — "One AI. Every
   Conversation": the solid CORE is the single unified AI brain; the
   unbroken RING is the always-on, 24/7 nature of the service; the bright
   NODE riding the ring is a live conversation in orbit around that one AI.
   It reads as a confident, tech-forward "O" (Ora / One) at any size, with
   no generic speech-bubble cliché and no letterform to decode.

   Exports (kept backward-compatible with the previous logo):
     • <Logo />        full lockup (mark + "Ora One" wordmark [+ tagline])
     • <OraMark />     mark only (the master brand mark)
     • <BrandMark />   alias of OraMark
     • <AppIcon />     mark reversed to white inside a solid gradient
                       rounded-square tile — dedicated favicon/app-icon
                       derivative, NEVER used as the primary logo
     • BRAND_LOGO_URL / BRAND_MARK_URL / BRAND_WORDMARK_URL (legacy fallbacks)
   ========================================================================= */

export const BRAND_LOGO_URL = "/assets/brand-logo.png";
export const BRAND_MARK_URL = "/assets/oraone-mark.png";
export const BRAND_WORDMARK_URL = "/assets/brand-logo.png";

// The master brand mark — the OraOne swirl emblem (raster, transparent).
export const MARK_SRC = "/assets/oraone-mark.png";

/**
 * OraMark — the OraOne swirl emblem (gradient orbit + conversation wave +
 * spark), the master brand mark. It is a full-colour glyph that reads on
 * both light and dark surfaces, so `light` is accepted for API
 * compatibility but does not change the artwork.
 */
export function OraMark({ size = 40, className = "", light = false, style, ...rest }) {
  return (
    <img
      src={MARK_SRC}
      width={size}
      height={size}
      className={className}
      alt=""
      aria-hidden="true"
      draggable="false"
      decoding="async"
      style={{ objectFit: "contain", ...style }}
      {...rest}
    />
  );
}

// Backward-compatible alias
export function BrandMark(props) {
  return <OraMark {...props} />;
}

/**
 * AppIcon — the swirl emblem inside a rounded dark tile, the dedicated
 * favicon/app-icon derivative for square icon slots. NOT an alternate logo.
 */
export function AppIcon({ size = 40, className = "", style, ...rest }) {
  return (
    <span
      className={className}
      style={{
        display: "inline-flex",
        width: size,
        height: size,
        borderRadius: size * 0.26,
        background: "#0A1B3A",
        alignItems: "center",
        justifyContent: "center",
        ...style,
      }}
      {...rest}
    >
      <img
        src={MARK_SRC}
        width={Math.round(size * 0.72)}
        height={Math.round(size * 0.72)}
        alt=""
        aria-hidden="true"
        draggable="false"
        style={{ objectFit: "contain" }}
      />
    </span>
  );
}

/**
 * Logo — full horizontal lockup: orb mark + "Ora One" wordmark.
 *
 * Props:
 *   className    — sizing class (height-based, e.g. "h-9"). Default "h-9".
 *   light        — white mark + wordmark for dark surfaces.
 *   showWordmark — hide text to render mark-only. Default true.
 *   showTagline  — show "One AI. Every Conversation." beneath. Default false.
 *   stacked      — vertical lockup (mark above wordmark). Default false.
 */
export function Logo({
  className = "h-9",
  light = false,
  showWordmark = true,
  showTagline = false,
  stacked = false,
  ...rest
}) {
  const sizeMap = { "h-6": 24, "h-7": 28, "h-8": 32, "h-9": 36, "h-10": 40, "h-11": 44, "h-12": 48, "h-14": 56, "h-16": 64, "h-20": 80, "h-24": 96 };
  const heightClass = (className.match(/h-\d+/) || ["h-9"])[0];
  const orbSize = sizeMap[heightClass] || 36;
  const wordSize = orbSize * (stacked ? 0.74 : 0.66);

  const wordmark = (
    <span className="font-extrabold tracking-tight leading-none" style={{ fontSize: wordSize }}>
      <span style={{ color: light ? "#FFFFFF" : "#0A1B3A" }}>Ora</span>
      <span
        style={{
          backgroundImage: "linear-gradient(90deg,#2563EB 0%,#7C3AED 55%,#DB2777 100%)",
          WebkitBackgroundClip: "text",
          backgroundClip: "text",
          WebkitTextFillColor: "transparent",
          color: "transparent",
        }}
      >
        One
      </span>
    </span>
  );

  if (stacked) {
    return (
      <span className="inline-flex flex-col items-center gap-2 select-none" {...rest}>
        <OraMark size={orbSize} light={light} />
        {showWordmark && wordmark}
        {showTagline && <Tagline size={wordSize} light={light} />}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-2.5 select-none" {...rest}>
      <OraMark size={orbSize} light={light} />
      {showWordmark && (
        <span className="inline-flex flex-col">
          {wordmark}
          {showTagline && <Tagline size={wordSize} light={light} />}
        </span>
      )}
    </span>
  );
}

/** Tagline with flanking rules: "One AI. Every Conversation." */
function Tagline({ size = 24, light = false }) {
  return (
    <span
      className="mt-1 inline-flex items-center gap-1.5"
      style={{ fontSize: Math.max(9, size * 0.34) }}
    >
      <span className="h-px w-3" style={{ background: light ? "#7DD3FC" : "#1E73E8" }} />
      <span
        className="font-semibold tracking-tight whitespace-nowrap"
        style={{ color: light ? "rgba(255,255,255,0.75)" : "#475569" }}
      >
        One AI. Every Conversation.
      </span>
      <span className="h-px w-3" style={{ background: light ? "#7DD3FC" : "#1E73E8" }} />
    </span>
  );
}

export default Logo;
