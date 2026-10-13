"use strict";

// CommonJS distribution kept in lockstep with src/index.js.
const DEFAULT_CDN = "https://oraone.in/widget.js";
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

let injected = false;
const queued = [];
let flushTimer = null;
let flushDeadline = 0;
const LOAD_TIMEOUT_MS = 30000;
const isBrowser = () =>
  typeof window !== "undefined" && typeof document !== "undefined";

function ensureScript(options) {
  if (!isBrowser() || injected) return;
  injected = true;
  let script = document.querySelector("script[data-oraone-loader]");
  if (!script) {
    script = document.createElement("script");
    script.src = options.src || DEFAULT_CDN;
    script.setAttribute("data-oraone-loader", "1");
    if (options.agentId) script.setAttribute("data-widget-id", options.agentId);
    if (options.apiBase) script.setAttribute("data-api", options.apiBase);
    script.async = true;
    script.addEventListener("load", flushWhenReady, { once: true });
    script.addEventListener("error", handleLoadError, { once: true });
    document.head.appendChild(script);
  } else if (!window.OraOne) {
    script.addEventListener("load", flushWhenReady, { once: true });
  }
}

function flushWhenReady() {
  if (!isBrowser() || !queued.length) return;
  const widget = window.OraOne;
  if (widget) {
    if (flushTimer) clearTimeout(flushTimer);
    flushTimer = null;
    while (queued.length) {
      const [method, args] = queued.shift();
      if (typeof widget[method] === "function")
        widget[method].apply(null, args);
    }
    return;
  }
  if (flushTimer) return;
  if (!flushDeadline) flushDeadline = Date.now() + LOAD_TIMEOUT_MS;
  flushTimer = setTimeout(() => {
    flushTimer = null;
    if (!queued.length) {
      flushDeadline = 0;
      return;
    }
    if (window.OraOne || Date.now() < flushDeadline) {
      flushWhenReady();
    } else {
      queued.length = 0;
      flushDeadline = 0;
      console.error(
        "[OraOne] Widget loader did not become ready; queued calls were discarded.",
      );
    }
  }, 50);
}

function handleLoadError() {
  injected = false;
  if (flushTimer) clearTimeout(flushTimer);
  flushTimer = null;
  flushDeadline = 0;
  queued.length = 0;
  console.error(
    "[OraOne] Widget loader failed to load; queued calls were discarded.",
  );
}

function call(method, args) {
  if (!isBrowser()) return OraOne;
  const widget = window.OraOne;
  if (widget && typeof widget[method] === "function")
    widget[method].apply(null, args);
  else {
    queued.push([method, args]);
    flushWhenReady();
  }
  return OraOne;
}

function init(options = {}) {
  ensureScript(options);
  if (options.user || options.identify)
    call("identifyUser", [options.user || options.identify]);
  if (options.context) call("updateContext", [options.context]);
  if (options.autoOpen) call("open", []);
  call("init", [options]);
  return OraOne;
}

const OraOne = { init };
METHODS.forEach((method) => {
  OraOne[method] = (...args) => call(method, args);
});

module.exports = OraOne;
module.exports.OraOne = OraOne;
module.exports.OraOneWidget = OraOne;
module.exports.default = OraOne;
