/**
 * @oraone/widget — the official OraOne SDK.
 *
 * A tiny (zero-dependency) wrapper that injects the OraOne widget loader and
 * gives you a typed, promise-safe `OraOne` surface you can call from React,
 * Next.js, Vue, Angular, Svelte or plain JS. Every call made before the
 * loader finishes is buffered and replayed, so ordering never matters.
 *
 *   import { OraOne } from '@oraone/widget';
 *   OraOne.init({ agentId: 'wgt_xxx' });
 *   OraOne.identifyUser({ name: 'Asha', email: 'asha@acme.com' });
 *   OraOne.startChat('I need pricing help');
 */

const DEFAULT_CDN = "https://oraone.in/widget.js";

// Public method surface — mirrors window.OraOne defined by widget.js.
const METHODS = [
  "identifyUser",
  "updateContext",
  "sendEvent",
  "trackEvent",
  "setLeadData",
  "trackPurchase",
  "open",
  "close",
  "toggle",
  "openChat",
  "closeChat",
  "toggleChat",
  "startChat",
];

let _injected = false;
const _pre = []; // calls buffered before window.OraOne exists
let _flushTimer = null;
let _flushDeadline = 0;
const LOAD_TIMEOUT_MS = 30_000;

function isBrowser() {
  return typeof window !== "undefined" && typeof document !== "undefined";
}

function ensureScript(opts) {
  if (!isBrowser() || _injected) return;
  _injected = true;
  // Reuse an existing tag if the host already embedded the loader.
  let script = document.querySelector("script[data-oraone-loader]");
  if (!script) {
    script = document.createElement("script");
    script.src = opts.src || DEFAULT_CDN;
    script.setAttribute("data-oraone-loader", "1");
    if (opts.agentId) script.setAttribute("data-widget-id", opts.agentId);
    if (opts.apiBase) script.setAttribute("data-api", opts.apiBase);
    script.async = true;
    script.addEventListener("load", flushWhenReady, { once: true });
    script.addEventListener("error", handleLoadError, { once: true });
    document.head.appendChild(script);
  } else if (!window.OraOne) {
    // The host may have added its embed tag but the loader has not finished.
    script.addEventListener("load", flushWhenReady, { once: true });
  }
}

function flushWhenReady() {
  if (!isBrowser() || !_pre.length) return;
  const widget = window.OraOne;
  if (widget) {
    if (_flushTimer) clearTimeout(_flushTimer);
    _flushTimer = null;
    while (_pre.length) {
      const [method, args] = _pre.shift();
      if (typeof widget[method] === "function") {
        widget[method].apply(null, args);
      }
    }
    return;
  }
  if (_flushTimer) return;
  if (!_flushDeadline) _flushDeadline = Date.now() + LOAD_TIMEOUT_MS;
  _flushTimer = setTimeout(() => {
    _flushTimer = null;
    if (!_pre.length) {
      _flushDeadline = 0;
      return;
    }
    if (window.OraOne) {
      flushWhenReady();
    } else if (Date.now() < _flushDeadline) {
      flushWhenReady();
    } else {
      _pre.length = 0;
      _flushDeadline = 0;
      console.error(
        "[OraOne] Widget loader did not become ready; queued calls were discarded.",
      );
    }
  }, 50);
}

function handleLoadError() {
  _injected = false;
  if (_flushTimer) clearTimeout(_flushTimer);
  _flushTimer = null;
  _flushDeadline = 0;
  _pre.length = 0;
  console.error(
    "[OraOne] Widget loader failed to load; queued calls were discarded.",
  );
}

function call(method, args) {
  if (!isBrowser()) return OraOne; // SSR no-op
  const w = window.OraOne;
  if (w && typeof w[method] === "function") {
    w[method].apply(null, args);
  } else {
    _pre.push([method, args]);
    flushWhenReady();
  }
  return OraOne;
}

/**
 * Boot the widget. `agentId` is your widget public key (wgt_…).
 * Optional: { apiBase, src, user, context, autoOpen }.
 */
function init(options) {
  options = options || {};
  ensureScript(options);
  if (options.user || options.identify)
    call("identifyUser", [options.user || options.identify]);
  if (options.context) call("updateContext", [options.context]);
  if (options.autoOpen) call("open", []);
  // Forward to the loader's own init once available (idempotent).
  call("init", [options]);
  return OraOne;
}

export const OraOne = { init };
METHODS.forEach((m) => {
  OraOne[m] = function () {
    return call(m, Array.prototype.slice.call(arguments));
  };
});

// Back-compat alias for the legacy named export.
export const OraOneWidget = OraOne;
export default OraOne;
