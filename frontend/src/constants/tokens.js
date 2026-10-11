// ─────────────────────────────────────────────────────────────────────────────
// OraOne Visual Design System — tokens (VDS v1)
//
// Single source of truth for the product's visual language. Consumed both in
// JS (inline styles, chart colors) and, via `tailwind.config.js`, as semantic
// utility classes (e.g. `text-ink`, `bg-brand-soft`, `border-line`,
// `shadow-card`, `rounded-card`).
//
// Rule: never hardcode a hex, radius, or shadow in a component — reference a
// token here (or its Tailwind semantic class) so the whole app moves together.
// ─────────────────────────────────────────────────────────────────────────────

/* Color — semantic, not literal. */
export const COLOR = {
  // Brand / primary action
  brand: "#2563EB",
  brandHover: "#1D4ED8",
  brandSoft: "#EFF4FF",
  brandSoftAlt: "#EFF6FF",

  // Text / ink scale
  ink: "#0F172A", // primary text & headings
  body: "#334155", // body copy
  sub: "#64748B", // secondary text
  faint: "#94A3B8", // tertiary / captions

  // Lines & surfaces
  line: "#EAF0F6", // card borders
  hairline: "#F1F5F9", // internal dividers
  stroke: "#E2E8F0", // control borders (inputs, buttons)
  canvas: "#F6F8FC", // app background
  surface: "#FFFFFF", // cards
  subtle: "#FBFCFE", // subtle raised rows / tiles
  wash: "#F8FAFC", // hover wash

  // Status
  success: "#16A34A",
  successSoft: "#ECFDF3",
  successInk: "#067647",
  warning: "#F59E0B",
  warningSoft: "#FFF7ED",
  warningInk: "#B45309",
  danger: "#B42318",
  dangerSoft: "#FEF3F2",
  dangerBorder: "#FEE4E2",
  info: "#0891B2",
  infoSoft: "#ECFEFF",

  // Accent chips (soft icon backgrounds)
  violet: "#7C3AED",
  violetSoft: "#F5F3FF",
  amber: "#F59E0B",
  amberSoft: "#FFF7ED",
  cyan: "#0891B2",
  cyanSoft: "#ECFEFF",
};

/* Border radius — 4px rhythm. `card` matches Tailwind rounded-2xl. */
export const RADIUS = {
  sm: "8px",
  md: "12px",
  lg: "16px",
  card: "16px",
  xl: "20px",
  pill: "9999px",
};

/* Elevation — three tiers only. */
export const SHADOW = {
  card: "0 1px 2px rgba(16,24,40,0.04)",
  cardHover: "0 8px 24px -12px rgba(16,24,40,0.16)",
  pop: "0 12px 32px -12px rgba(16,24,40,0.24)",
};

/* Spacing scale — 4px base. */
export const SPACE = {
  xs: "4px",
  sm: "8px",
  md: "12px",
  lg: "16px",
  xl: "24px",
  "2xl": "32px",
};

/* Typography — semantic roles. */
export const FONT = {
  caption: "12px",
  body: "13.5px",
  bodyLg: "14.5px",
  h3: "15px",
  h2: "18px",
  h1: "28px",
};

/* Motion — one duration/easing vocabulary for the whole app. */
export const MOTION = {
  fast: 0.18,
  base: 0.24,
  slow: 0.28,
  ease: [0.22, 1, 0.36, 1], // standard ease-out for enter transitions
};

export default { COLOR, RADIUS, SHADOW, SPACE, FONT, MOTION };
