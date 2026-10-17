/*!
 * OraOne website chat widget (loader and SDK) — version 1.0.0
 *
 * Embed with one script tag:
 *   <script src="https://YOUR-DOMAIN/widget.js" data-widget-id="PUBLIC_KEY" async></script>
 *
 * Optional attributes:
 *   data-api       Base URL of the OraOne API when it is not the script's origin.
 *   data-open="true" Open the chat panel on load.
 *
 * SDK (available once the script has loaded):
 *   window.OraOne.open()            show the chat panel
 *   window.OraOne.close()           hide the chat panel
 *   window.OraOne.toggle()          switch the panel open or closed
 *   window.OraOne.send("text")      send a visitor message programmatically
 *   window.OraOne.identify({...})   attach non-secret context (for example plan or email)
 *   window.OraOne.destroy()         remove the widget from the page
 *
 * The widget renders inside a Shadow DOM, so host-page CSS cannot change its
 * appearance. All visitor and assistant text is inserted as plain text.
 */
(function () {
  "use strict";

  if (window.OraOne && window.OraOne.__loaded) return;

  var VERSION = "1.0.0";
  var STORAGE_PREFIX = "oraone:visitor:";
  var SESSION_PREFIX = "oraone:session:";
  var SESSION_HEADER = "X-Widget-Session";
  var DEFAULT_SUGGESTIONS = [];

  var script = document.currentScript || document.querySelector("script[data-widget-id]");
  var publicKey = script && script.getAttribute("data-widget-id");
  if (!publicKey) {
    console.error("[OraOne] Missing data-widget-id on the widget script tag.");
    return;
  }

  var apiBase = (
    (script && script.getAttribute("data-api")) ||
    (script && script.src ? new URL(script.src).origin : window.location.origin)
  ).replace(/\/+$/, "");

  var state = {
    config: null,
    open: false,
    sessionId: null,
    conversationId: null,
    visitorId: visitorId(),
    context: {},
    busy: false,
    host: null,
    root: null,
    refs: {},
    sessionToken: null,
  };

  var restored = storedSession();
  if (restored) {
    state.visitorId = restored.visitorId;
    state.sessionToken = restored.token;
  }

  // ───────────────────────── helpers ─────────────────────────

  // The session token is kept in sessionStorage (per tab, per widget key), never
  // in localStorage. It is stored with the visitor id it was issued for.
  function storedSession() {
    try {
      var raw = window.sessionStorage.getItem(SESSION_PREFIX + publicKey);
      var saved = raw ? JSON.parse(raw) : null;
      return saved && saved.visitorId && saved.token ? saved : null;
    } catch (err) {
      return null;
    }
  }

  function rememberSession(visitorIdValue, token) {
    state.visitorId = visitorIdValue;
    state.sessionToken = token;
    try {
      window.sessionStorage.setItem(
        SESSION_PREFIX + publicKey,
        JSON.stringify({ visitorId: visitorIdValue, token: token }),
      );
    } catch (err) {
      // Storage can be blocked. The token still works for this page load.
    }
  }

  // Drop the token so the next message starts a fresh visitor session.
  function forgetSession() {
    state.sessionToken = null;
    state.sessionId = null;
    state.conversationId = null;
    sessionPromise = null;
    try {
      window.sessionStorage.removeItem(SESSION_PREFIX + publicKey);
    } catch (err) {
      // Nothing to clean up when storage is unavailable.
    }
  }

  function visitorId() {
    var key = STORAGE_PREFIX + publicKey;
    try {
      var saved = window.localStorage.getItem(key);
      if (saved) return saved;
      var created = "v_" + randomHex(16);
      window.localStorage.setItem(key, created);
      return created;
    } catch (err) {
      // Storage can be blocked (private mode, strict settings). A per-page id still works.
      return "v_" + randomHex(16);
    }
  }

  function randomHex(length) {
    var out = "";
    var bytes = new Uint8Array(length / 2);
    if (window.crypto && window.crypto.getRandomValues) {
      window.crypto.getRandomValues(bytes);
    } else {
      for (var i = 0; i < bytes.length; i += 1) bytes[i] = Math.floor(Math.random() * 256);
    }
    for (var j = 0; j < bytes.length; j += 1) {
      out += ("0" + bytes[j].toString(16)).slice(-2);
    }
    return out;
  }

  function request(path, body) {
    var headers = { "Content-Type": "application/json" };
    if (state.sessionToken) headers[SESSION_HEADER] = state.sessionToken;
    var options = {
      method: body ? "POST" : "GET",
      headers: headers,
      credentials: "omit",
    };
    if (body) options.body = JSON.stringify(body);
    return window.fetch(apiBase + path, options).then(function (response) {
      return response
        .json()
        .catch(function () {
          return {};
        })
        .then(function (data) {
          if (!response.ok) {
            var error = new Error(data.detail || "Request failed.");
            error.status = response.status;
            // A rejected token means this visitor session is no longer valid.
            if ((response.status === 401 || response.status === 403) && state.sessionToken) {
              forgetSession();
            }
            throw error;
          }
          return data;
        });
    });
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function safeColor(value, fallback) {
    return typeof value === "string" && /^#[0-9a-fA-F]{3,8}$/.test(value) ? value : fallback;
  }

  function safeRadius(value) {
    return typeof value === "string" && /^[0-9.]+(px|rem)$/.test(value) ? value : "16px";
  }

  // ───────────────────────── rendering ─────────────────────────

  function buildStyles(theme) {
    var primary = safeColor(theme.primary_color, "#2563EB");
    var bubble = safeColor(theme.bubble_color, primary);
    var background = safeColor(theme.background_color, "#FFFFFF");
    var text = safeColor(theme.text_color, "#0F172A");
    var radius = safeRadius(theme.radius);
    var side = (state.config.position || "bottom-right").indexOf("left") >= 0 ? "left" : "right";
    return [
      ":host{all:initial}",
      "*{box-sizing:border-box;font-family:Inter,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}",
      ".launcher{position:fixed;bottom:20px;" +
        side +
        ":20px;width:56px;height:56px;border-radius:999px;border:0;cursor:pointer;background:" +
        bubble +
        ";color:#fff;box-shadow:0 8px 24px rgba(15,23,42,.25);display:flex;align-items:center;justify-content:center;font-size:24px;z-index:2147483000}",
      ".launcher:focus-visible,.send:focus-visible,.close:focus-visible,.chip:focus-visible{outline:3px solid " +
        primary +
        ";outline-offset:2px}",
      ".panel{position:fixed;bottom:88px;" +
        side +
        ":20px;width:min(380px,calc(100vw - 32px));height:min(560px,calc(100vh - 120px));display:none;flex-direction:column;background:" +
        background +
        ";color:" +
        text +
        ";border-radius:" +
        radius +
        ";box-shadow:0 16px 48px rgba(15,23,42,.28);overflow:hidden;z-index:2147483000}",
      ".panel.open{display:flex}",
      ".head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 18px;background:" +
        primary +
        ";color:#fff}",
      ".title{font-size:16px;font-weight:600;margin:0}",
      ".close{background:transparent;border:0;color:#fff;font-size:22px;line-height:1;cursor:pointer;padding:4px}",
      ".log{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}",
      ".msg{max-width:85%;padding:10px 14px;border-radius:14px;font-size:15px;line-height:1.5;white-space:pre-wrap;word-wrap:break-word}",
      ".msg.user{align-self:flex-end;background:" +
        primary +
        ";color:#fff;border-bottom-" +
        (side === "right" ? "right" : "left") +
        "-radius:4px}",
      ".msg.assistant{align-self:flex-start;background:#F1F5F9;color:" +
        text +
        ";border-bottom-" +
        (side === "right" ? "left" : "right") +
        "-radius:4px}",
      ".msg.notice{align-self:center;background:transparent;color:#64748B;font-size:13px}",
      ".chips{display:flex;flex-wrap:wrap;gap:8px;padding:0 16px 12px}",
      ".chip{border:1px solid " +
        primary +
        ";background:transparent;color:" +
        primary +
        ";border-radius:999px;padding:6px 12px;font-size:13px;cursor:pointer}",
      ".form{display:flex;gap:8px;padding:12px;border-top:1px solid #E2E8F0}",
      ".input{flex:1;min-height:44px;max-height:120px;resize:none;border:1px solid #CBD5E1;border-radius:12px;padding:10px 12px;font-size:15px;color:" +
        text +
        ";background:#fff}",
      ".input:focus-visible{outline:3px solid " + primary + ";outline-offset:1px}",
      ".send{border:0;border-radius:12px;background:" +
        primary +
        ";color:#fff;padding:0 16px;font-size:15px;font-weight:600;cursor:pointer;min-width:64px}",
      ".send:disabled{opacity:.55;cursor:not-allowed}",
      ".brand{font-size:12px;color:#64748B;text-align:center;padding:0 0 10px}",
      ".brand a{color:inherit}",
      "@media (max-width:480px){.panel{bottom:0;left:0;right:0;width:100%;height:100%;border-radius:0}.launcher{bottom:16px;" +
        side +
        ":16px}}",
    ].join("");
  }

  function render() {
    var theme = state.config.theme || {};
    var settings = state.config.settings || {};

    state.host = el("div");
    state.host.setAttribute("data-oraone-widget", publicKey);
    var shadow = state.host.attachShadow({ mode: "open" });
    var style = el("style");
    style.textContent = buildStyles(theme);
    shadow.appendChild(style);

    var launcher = el("button", "launcher", "💬");
    launcher.type = "button";
    launcher.setAttribute("aria-label", "Open chat");
    launcher.setAttribute("aria-expanded", "false");
    launcher.setAttribute("aria-controls", "oraone-panel");

    var panel = el("section", "panel");
    panel.id = "oraone-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", state.config.name || "Chat");

    var head = el("div", "head");
    var title = el("p", "title", settings.agent_name || "Ora AI");
    var close = el("button", "close", "×");
    close.type = "button";
    close.setAttribute("aria-label", "Close chat");
    head.appendChild(title);
    head.appendChild(close);

    var log = el("div", "log");
    log.setAttribute("role", "log");
    log.setAttribute("aria-live", "polite");

    var chips = el("div", "chips");
    var form = el("form", "form");
    var input = el("textarea", "input");
    input.rows = 1;
    input.placeholder = settings.input_placeholder || "Ask a question…";
    input.setAttribute("aria-label", "Your message");
    var send = el("button", "send", "Send");
    send.type = "submit";
    form.appendChild(input);
    form.appendChild(send);

    panel.appendChild(head);
    panel.appendChild(log);
    panel.appendChild(chips);
    panel.appendChild(form);
    if (settings.show_branding !== false) {
      var brand = el("p", "brand");
      brand.appendChild(document.createTextNode("Powered by "));
      var link = el("a", null, "OraOne");
      link.href = "https://oraone.in";
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      brand.appendChild(link);
      panel.appendChild(brand);
    }

    shadow.appendChild(launcher);
    shadow.appendChild(panel);
    document.body.appendChild(state.host);

    state.root = panel;
    state.refs = {
      launcher: launcher,
      panel: panel,
      log: log,
      chips: chips,
      input: input,
      send: send,
    };

    launcher.addEventListener("click", toggle);
    close.addEventListener("click", closePanel);
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      submit();
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        submit();
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && state.open) closePanel();
    });
  }

  function addMessage(role, text) {
    var node = el("div", "msg " + role, text);
    state.refs.log.appendChild(node);
    state.refs.log.scrollTop = state.refs.log.scrollHeight;
    return node;
  }

  function renderSuggestions(list) {
    var chips = state.refs.chips;
    chips.textContent = "";
    (list || []).slice(0, 4).forEach(function (question) {
      var chip = el("button", "chip", question);
      chip.type = "button";
      chip.addEventListener("click", function () {
        send(question);
      });
      chips.appendChild(chip);
    });
  }

  // ───────────────────────── behaviour ─────────────────────────

  function openPanel() {
    state.open = true;
    state.refs.panel.classList.add("open");
    state.refs.launcher.setAttribute("aria-expanded", "true");
    state.refs.input.focus();
    ensureSession();
  }

  function closePanel() {
    state.open = false;
    state.refs.panel.classList.remove("open");
    state.refs.launcher.setAttribute("aria-expanded", "false");
    state.refs.launcher.focus();
  }

  function toggle() {
    if (state.open) closePanel();
    else openPanel();
  }

  var sessionPromise = null;

  function ensureSession() {
    if (sessionPromise) return sessionPromise;
    sessionPromise = request("/api/widget/session", {
      public_key: publicKey,
      visitor_id: state.visitorId,
      user_context: state.context,
    }).then(
      function (data) {
        state.sessionId = data.session_id;
        state.conversationId = data.conversation_id;
        if (data.session_token) {
          rememberSession(data.visitor_id || state.visitorId, data.session_token);
        } else if (data.visitor_id) {
          state.visitorId = data.visitor_id;
        }
        var history = data.messages || [];
        if (history.length) {
          history.forEach(function (m) {
            addMessage(m.role === "assistant" ? "assistant" : "user", m.content);
          });
        } else {
          addMessage(
            "assistant",
            (state.config.settings || {}).welcome_message || "Hi! How can I help?",
          );
          renderSuggestions(
            (state.config.settings || {}).suggested_questions || DEFAULT_SUGGESTIONS,
          );
        }
        return data;
      },
      function (error) {
        sessionPromise = null;
        addMessage("notice", offlineText(error));
        state.refs.input.disabled = true;
        state.refs.send.disabled = true;
        throw error;
      },
    );
    return sessionPromise;
  }

  function offlineText(error) {
    var settings = (state.config && state.config.settings) || {};
    if (error && (error.status === 403 || error.status === 404)) {
      return settings.offline_message || "This chat is not available right now.";
    }
    return "We couldn't connect. Please try again in a moment.";
  }

  function submit() {
    var text = state.refs.input.value.trim();
    if (!text) return;
    state.refs.input.value = "";
    send(text);
  }

  function send(text) {
    if (state.busy || !text) return;
    if (!state.open) openPanel();
    state.busy = true;
    state.refs.send.disabled = true;
    state.refs.chips.textContent = "";
    addMessage("user", text);
    var thinking = addMessage("assistant", "…");
    thinking.setAttribute("aria-label", "Assistant is typing");

    ensureSession()
      .then(function () {
        return request("/api/widget/chat", {
          public_key: publicKey,
          visitor_id: state.visitorId,
          message: text,
          session_id: state.sessionId,
          user_context: state.context,
        });
      })
      .then(function (data) {
        state.sessionId = data.session_id || state.sessionId;
        state.conversationId = data.conversation_id || state.conversationId;
        if (data.session_token) rememberSession(state.visitorId, data.session_token);
        thinking.textContent = data.answer || "";
        renderSuggestions(data.related_questions);
      })
      .catch(function (error) {
        thinking.className = "msg notice";
        thinking.textContent = offlineText(error);
      })
      .then(function () {
        state.busy = false;
        state.refs.send.disabled = false;
        state.refs.input.focus();
      });
  }

  // ───────────────────────── public SDK ─────────────────────────

  function destroy() {
    if (state.host && state.host.parentNode) state.host.parentNode.removeChild(state.host);
    window.OraOne = { __loaded: false, version: VERSION };
  }

  function boot() {
    request("/api/widget/config?key=" + encodeURIComponent(publicKey))
      .then(function (config) {
        state.config = config;
        render();
        if (script && script.getAttribute("data-open") === "true") openPanel();
      })
      .catch(function () {
        console.warn("[OraOne] The chat widget could not be loaded for this domain.");
      });
  }

  window.OraOne = {
    __loaded: true,
    version: VERSION,
    open: function () {
      if (state.refs.panel) openPanel();
    },
    close: function () {
      if (state.refs.panel) closePanel();
    },
    toggle: function () {
      if (state.refs.panel) toggle();
    },
    send: function (text) {
      if (state.refs.panel) send(String(text || "").slice(0, 4000));
    },
    identify: function (context) {
      if (context && typeof context === "object") {
        state.context = Object.assign({}, state.context, context);
      }
    },
    destroy: destroy,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
