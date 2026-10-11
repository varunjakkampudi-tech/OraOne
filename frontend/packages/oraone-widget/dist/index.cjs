'use strict';

// CommonJS distribution kept in lockstep with src/index.js.
const DEFAULT_CDN = 'https://oraone.in/widget.js';
const METHODS = [
  'identifyUser', 'updateContext', 'sendEvent', 'trackEvent', 'setLeadData',
  'trackPurchase', 'open', 'close', 'toggle', 'openChat', 'closeChat',
  'toggleChat', 'startChat',
];

let injected = false;
const queued = [];
const isBrowser = () => typeof window !== 'undefined' && typeof document !== 'undefined';

function ensureScript(options) {
  if (!isBrowser() || injected) return;
  injected = true;
  if (document.querySelector('script[data-oraone-loader]')) return;
  const script = document.createElement('script');
  script.src = options.src || DEFAULT_CDN;
  script.setAttribute('data-oraone-loader', '1');
  if (options.agentId) script.setAttribute('data-widget-id', options.agentId);
  if (options.apiBase) script.setAttribute('data-api', options.apiBase);
  script.async = true;
  document.head.appendChild(script);
  flushWhenReady();
}

function flushWhenReady() {
  if (!isBrowser()) return;
  const tick = () => {
    const widget = window.OraOne;
    if (widget && queued.length) {
      while (queued.length) {
        const [method, args] = queued.shift();
        if (typeof widget[method] === 'function') widget[method].apply(null, args);
      }
    }
    if (queued.length) setTimeout(tick, 50);
  };
  tick();
}

function call(method, args) {
  if (!isBrowser()) return OraOne;
  const widget = window.OraOne;
  if (widget && typeof widget[method] === 'function') widget[method].apply(null, args);
  else queued.push([method, args]);
  return OraOne;
}

function init(options = {}) {
  ensureScript(options);
  if (options.user || options.identify) call('identifyUser', [options.user || options.identify]);
  if (options.context) call('updateContext', [options.context]);
  if (options.autoOpen) call('open', []);
  call('init', [options]);
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
