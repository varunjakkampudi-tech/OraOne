// /app/frontend/src/lib/analytics.js
// Lightweight, plug-and-play analytics layer for OraOne.
//
// Why this file exists
// ────────────────────
// We DON'T ship keys yet (GA4 Measurement ID, Microsoft Clarity ID, PostHog key
// will come later). But every product event still needs a single, consistent
// place to be fired from so that wiring real providers later is one-line work.
//
// Public API
// ──────────
//   import { track, EVENTS } from "@/lib/analytics";
//   track(EVENTS.SIGNUP, { plan: "growth" });
//
// Providers (GA4 / Clarity / PostHog) are auto-detected at runtime and the
// event is forwarded to whichever is loaded — no further wiring needed.
//
// Consent
// ───────
// `setConsent({analytics: true})` is read from the CookieConsent component.
// Events are buffered until consent is granted (or rejected → buffer cleared).

const STORAGE_KEY = "oraone_analytics_consent";

/** Canonical event name registry — keep in sync with product specs. */
export const EVENTS = Object.freeze({
  PAGE_VIEW:          "page_view",
  SIGNUP:             "signup",
  LOGIN:              "login",
  LOGOUT:             "logout",
  CREATE_AGENT:       "create_agent",
  CONNECT_WHATSAPP:   "connect_whatsapp",
  CONNECT_INTEGRATION:"connect_integration",
  CREATE_LEAD:        "create_lead",
  EXPORT_LEADS:       "export_leads",
  BOOK_DEMO:          "book_demo",
  START_FREE:         "start_free",
  DEPLOY_TEMPLATE:    "deploy_template",
  UPLOAD_KNOWLEDGE:   "upload_knowledge",
  INVITE_TEAM:        "invite_team",
});

let buffer = [];
let consent = readConsent();

function readConsent() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/** Update consent and flush/discard the buffer accordingly. */
export function setConsent(next) {
  consent = next;
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* storage blocked */ }
  if (next?.analytics) {
    buffer.forEach(({ name, props }) => dispatch(name, props));
  }
  buffer = [];
}

export function getConsent() {
  return consent;
}

/** Forward to whichever provider is loaded. Silent in dev when none are. */
function dispatch(name, props) {
  // Google Analytics 4
  if (typeof window !== "undefined" && typeof window.gtag === "function") {
    window.gtag("event", name, props || {});
  }
  // PostHog
  if (typeof window !== "undefined" && window.posthog?.capture) {
    window.posthog.capture(name, props || {});
  }
  // Microsoft Clarity custom events
  if (typeof window !== "undefined" && typeof window.clarity === "function") {
    try { window.clarity("event", name); } catch { /* clarity rejects long names */ }
  }
  // Always emit a CustomEvent so test agents / Sentry breadcrumbs can listen
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("oraone:analytics", { detail: { name, props } }));
  }
}

/** Fire a single analytics event. */
export function track(name, props = {}) {
  if (!name) return;
  if (consent?.analytics) {
    dispatch(name, props);
  } else if (consent === null) {
    // No decision yet — buffer for later. Cap buffer at 50 to avoid leaks.
    if (buffer.length < 50) buffer.push({ name, props });
  }
  // If user rejected analytics we deliberately drop the event.
}

/** Identify the current user (no-op without provider). */
export function identify(userId, traits = {}) {
  if (!consent?.analytics || !userId) return;
  if (typeof window !== "undefined" && typeof window.gtag === "function") {
    window.gtag("set", "user_properties", traits);
    window.gtag("set", { user_id: userId });
  }
  if (typeof window !== "undefined" && window.posthog?.identify) {
    window.posthog.identify(userId, traits);
  }
}

/** Track page views (called on every route change). */
export function trackPageView(path) {
  track(EVENTS.PAGE_VIEW, { path: path || (typeof window !== "undefined" ? window.location.pathname : "") });
}
