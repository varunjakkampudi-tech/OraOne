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

const DEFAULT_CDN = 'https://oraone.in/widget.js';

// Public method surface — mirrors window.OraOne defined by widget.js.
const METHODS = [
  'identifyUser',
  'updateContext',
  'sendEvent',
  'trackEvent',
  'setLeadData',
  'trackPurchase',
  'open',
  'close',
  'toggle',
  'openChat',
  'closeChat',
  'toggleChat',
  'startChat',
];

let _injected = false;
const _pre = []; // calls buffered before window.OraOne exists

function isBrowser() {
  return typeof window !== 'undefined' && typeof document !== 'undefined';
}

function ensureScript(opts) {
  if (!isBrowser() || _injected) return;
  _injected = true;
  const src = opts.src || DEFAULT_CDN;
  // Reuse an existing tag if the host already embedded the loader.
  if (document.querySelector('script[data-oraone-loader]')) return;
  const s = document.createElement('script');
  s.src = src;
  s.setAttribute('data-oraone-loader', '1');
  if (opts.agentId) s.setAttribute('data-widget-id', opts.agentId);
  if (opts.apiBase) s.setAttribute('data-api', opts.apiBase);
  s.async = true;
  document.head.appendChild(s);
  flushWhenReady();
}

function flushWhenReady() {
  if (!isBrowser()) return;
  const tick = () => {
    const w = window.OraOne;
    if (w && _pre.length) {
      while (_pre.length) {
        const [m, args] = _pre.shift();
        if (typeof w[m] === 'function') w[m].apply(null, args);
      }
    }
    if (_pre.length) setTimeout(tick, 50);
  };
  tick();
}

function call(method, args) {
  if (!isBrowser()) return OraOne; // SSR no-op
  const w = window.OraOne;
  if (w && typeof w[method] === 'function') {
    w[method].apply(null, args);
  } else {
    _pre.push([method, args]);
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
  if (options.user || options.identify) call('identifyUser', [options.user || options.identify]);
  if (options.context) call('updateContext', [options.context]);
  if (options.autoOpen) call('open', []);
  // Forward to the loader's own init once available (idempotent).
  call('init', [options]);
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
