/*!
 * OraOne Embedded Website Widget — loader
 * Dependency-free. Drop-in: <script src=".../widget.js" data-widget-id="wgt_xxx" async></script>
 * Optional: data-api="https://api.example.com" to point at the backend when it
 * is served from a different origin than this script.
 */
(function () {
  "use strict";

  if (window.__oraoneWidgetLoaded) return;
  window.__oraoneWidgetLoaded = true;

  // ---- Locate this script + read configuration --------------------------------
  var script =
    document.currentScript ||
    (function () {
      var all = document.getElementsByTagName("script");
      for (var i = all.length - 1; i >= 0; i--) {
        if (all[i].src && all[i].src.indexOf("widget.js") !== -1) return all[i];
      }
      return all[all.length - 1];
    })();

  var widgetId = script.getAttribute("data-widget-id");
  if (!widgetId) {
    console.error("[OraOne] widget.js: missing data-widget-id");
    return;
  }

  function scriptOrigin() {
    try {
      return new URL(script.src, window.location.href).origin;
    } catch (e) {
      return window.location.origin;
    }
  }

  // Default API origin mirrors src/lib/api.js's resolveBackendUrl(): same
  // scheme, "api.<hostname>" of the domain widget.js itself is served from
  // (NOT the host page's domain — a customer embedding this on their own
  // site should still talk to OraOne's API, not a nonexistent
  // "api.<customer-domain>"). Without this, the default silently pointed at
  // the script's own origin (e.g. https://oraone.in/api/...), which has no
  // backend behind it, so every widget failed to load its config (404).
  function defaultApiOrigin() {
    var origin = scriptOrigin();
    try {
      var u = new URL(origin);
      if (u.hostname === "localhost" || u.hostname === "127.0.0.1") {
        return "http://127.0.0.1:8000";
      }
      var apexHost = u.hostname.replace(/^www\./, "");
      return u.protocol + "//api." + apexHost;
    } catch (e) {
      return origin;
    }
  }

  // API base: explicit data-api override, else derived "api.<domain>" origin.
  var apiBase = (script.getAttribute("data-api") || defaultApiOrigin()).replace(/\/+$/, "");
  var apiUrl = function (path) {
    return apiBase + "/api" + path;
  };

  // ---- Persistent visitor id --------------------------------------------------
  var VISITOR_KEY = "oraone_widget_visitor";
  var visitorId;
  try {
    visitorId = localStorage.getItem(VISITOR_KEY);
    if (!visitorId) {
      visitorId =
        "v_" +
        Date.now().toString(36) +
        Math.random().toString(36).slice(2, 10);
      localStorage.setItem(VISITOR_KEY, visitorId);
    }
  } catch (e) {
    visitorId = "v_" + Date.now().toString(36);
  }

  // Optional host-page supplied context (window.OraOneWidget = { user: {...} })
  function hostContext() {
    var ctx = (window.OraOneWidget && window.OraOneWidget.user) || {};
    var out = {};
    try {
      out.url = window.location.href;
      out.page_title = document.title;
    } catch (e) {}
    for (var k in ctx) {
      if (Object.prototype.hasOwnProperty.call(ctx, k)) out[k] = ctx[k];
    }
    return out;
  }

  function postEvent(event, metadata) {
    try {
      fetch(apiUrl("/widget/event"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          public_key: widgetId,
          visitor_id: visitorId,
          event: event,
          metadata: metadata || {},
        }),
        keepalive: true,
      }).catch(function () {});
    } catch (e) {}
  }

  // ---- Public SDK: window.OraOne.* (queued until the widget renders) ----------
  // One identity, one API surface. Calls made before the widget finishes
  // loading are buffered and replayed once it's ready.
  var _sdkReady = false;
  var _sdkQueue = [];
  var _sdkImpl = {};
  var SDK_METHODS = [
    "init",
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
  function defineSdk() {
    var api = window.OraOne || {};
    SDK_METHODS.forEach(function (m) {
      api[m] = function () {
        var args = arguments;
        if (_sdkReady && _sdkImpl[m]) return _sdkImpl[m].apply(null, args);
        _sdkQueue.push([m, args]);
        return api;
      };
    });
    api.visitorId = function () {
      return visitorId;
    };
    window.OraOne = api;
  }
  defineSdk();

  // ---- Fetch public config, then render ---------------------------------------
  fetch(apiUrl("/widget/config?key=" + encodeURIComponent(widgetId)))
    .then(function (r) {
      if (!r.ok) throw new Error("config " + r.status);
      return r.json();
    })
    .then(render)
    .catch(function (err) {
      var msg = (err && err.message) || "";
      // A 404 means this data-widget-id isn't provisioned (yet) — that's a
      // configuration state, not a runtime failure. The widget simply doesn't
      // render; warn (don't error) so an unconfigured/mistyped key degrades
      // quietly instead of surfacing a red console error on every page load.
      if (msg.indexOf("config 404") !== -1) {
        console.warn(
          "[OraOne] Chat widget not shown: no widget found for data-widget-id \"" +
            widgetId +
            "\". Double-check the key from your OraOne dashboard (Deploy)."
        );
      } else {
        console.error("[OraOne] widget config failed:", msg);
      }
    });

  function render(config) {
    var theme = config.theme || {};
    var settings = config.settings || {};
    var position = config.position || "bottom-right";
    var bubbleColor = theme.bubble_color || theme.primary_color || "#2563EB";
    var isLeft = position === "bottom-left";

    var side = isLeft ? "left" : "right";
    var Z = 2147483600;

    // ---- Launcher button ----
    var launcher = document.createElement("button");
    launcher.type = "button";
    launcher.id = "oraone-launcher";
    launcher.className = "oraone-launcher";
    launcher.setAttribute("aria-label", "Open chat");
    launcher.style.cssText =
      "position:fixed;bottom:20px;" +
      side +
      ":20px;width:60px;height:60px;border-radius:50%;border:none;cursor:pointer;" +
      "background:" +
      bubbleColor +
      ";box-shadow:0 6px 24px rgba(0,0,0,.22);z-index:" +
      Z +
      ";display:flex;align-items:center;justify-content:center;transition:transform .15s ease;padding:0;";
    launcher.innerHTML =
      '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">' +
      '<path d="M12 3C6.477 3 2 6.94 2 11.5c0 2.07.93 3.96 2.47 5.4-.1 1.2-.5 2.5-1.2 3.5-.2.3.03.7.4.62 1.7-.36 3.04-.96 3.95-1.5 1.32.45 2.78.7 4.38.7 5.523 0 10-3.94 10-8.72C22 6.94 17.523 3 12 3Z" fill="#fff"/>' +
      "</svg>";
    launcher.onmouseenter = function () {
      launcher.style.transform = "scale(1.06)";
    };
    launcher.onmouseleave = function () {
      launcher.style.transform = "scale(1)";
    };

    // ---- Panel + iframe ----
    var panel = document.createElement("div");
    panel.id = "oraone-panel";
    panel.className = "oraone-panel";
    panel.style.cssText =
      "position:fixed;bottom:92px;" +
      side +
      ":20px;width:380px;height:600px;max-width:calc(100vw - 32px);max-height:calc(100vh - 120px);" +
      "z-index:" +
      Z +
      ";border-radius:16px;overflow:hidden;box-shadow:0 12px 48px rgba(0,0,0,.28);" +
      "opacity:0;transform:translateY(12px) scale(.98);pointer-events:none;transition:opacity .18s ease,transform .18s ease;background:" +
      (theme.background_color || "#fff") +
      ";";

    var iframe = document.createElement("iframe");
    iframe.title = "OraOne chat";
    iframe.style.cssText = "width:100%;height:100%;border:0;display:block;";
    iframe.setAttribute("allow", "clipboard-write");
    iframe.srcdoc = buildAppHtml();
    panel.appendChild(iframe);

    document.body.appendChild(launcher);
    document.body.appendChild(panel);

    var open = false;
    var loaded = false;
    var pendingOpen = false;
    var pendingPrefill = null;

    function sendInit() {
      iframe.contentWindow.postMessage(
        {
          source: "oraone-host",
          type: "init",
          payload: {
            apiBase: apiBase,
            widgetId: widgetId,
            visitorId: visitorId,
            config: config,
            context: userContext,
          },
        },
        "*"
      );
    }

    function setOpen(next) {
      open = next;
      if (open) {
        panel.style.opacity = "1";
        panel.style.transform = "translateY(0) scale(1)";
        panel.style.pointerEvents = "auto";
        launcher.setAttribute("aria-label", "Close chat");
        postEvent("opened", {});
        if (loaded) iframe.contentWindow.postMessage({ source: "oraone-host", type: "focus" }, "*");
      } else {
        panel.style.opacity = "0";
        panel.style.transform = "translateY(12px) scale(.98)";
        panel.style.pointerEvents = "none";
        launcher.setAttribute("aria-label", "Open chat");
        postEvent("closed", {});
      }
    }

    launcher.addEventListener("click", function () {
      setOpen(!open);
    });

    window.addEventListener("message", function (ev) {
      var d = ev.data;
      if (!d || d.source !== "oraone-app") return;
      if (d.type === "ready") {
        loaded = true;
        sendInit();
        if (pendingOpen) setOpen(true);
        if (pendingPrefill) { pendingPrefill(); pendingPrefill = null; }
      } else if (d.type === "close") {
        setOpen(false);
      } else if (d.type === "event") {
        postEvent(d.event, d.metadata || {});
      }
    });

    postEvent("loaded", {});

    // Auto-open after popup_delay if configured as a popup type
    if (config.widget_type === "popup") {
      var delay = (settings.popup_delay_seconds || 0) * 1000;
      setTimeout(function () {
        if (!open) {
          if (loaded) setOpen(true);
          else pendingOpen = true;
        }
      }, delay);
    }

    // Expose a tiny programmatic API (legacy, kept for back-compat)
    window.OraOneWidget = window.OraOneWidget || {};
    window.OraOneWidget.open = function () {
      setOpen(true);
    };
    window.OraOneWidget.close = function () {
      setOpen(false);
    };
    window.OraOneWidget.toggle = function () {
      setOpen(!open);
    };

    // ---- Unified SDK implementation (window.OraOne.*) ----
    // Host-side merged context flows to the iframe (for live chat) AND is
    // persisted server-side so the SAME identity is recognised on other channels/forms.
    var userContext = hostContext();

    function pushContext() {
      if (loaded) {
        iframe.contentWindow.postMessage(
          { source: "oraone-host", type: "context", payload: userContext },
          "*"
        );
      }
    }
    function persistContext() {
      try {
        fetch(apiUrl("/widget/session"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            public_key: widgetId,
            visitor_id: visitorId,
            user_context: userContext,
          }),
          keepalive: true,
        }).catch(function () {});
      } catch (e) {}
    }
    function mergeContext(obj) {
      if (obj && typeof obj === "object") {
        for (var k in obj) {
          if (Object.prototype.hasOwnProperty.call(obj, k) && obj[k] != null) {
            userContext[k] = obj[k];
          }
        }
      }
      pushContext();
      persistContext();
      return window.OraOne;
    }

    _sdkImpl.identifyUser = mergeContext;
    _sdkImpl.updateContext = mergeContext;
    _sdkImpl.sendEvent = function (name, metadata) {
      postEvent(String(name || "custom"), metadata || {});
      return window.OraOne;
    };
    _sdkImpl.setLeadData = function (data) {
      mergeContext(data);
      try {
        var payload = { public_key: widgetId, visitor_id: visitorId };
        if (data && typeof data === "object") {
          for (var k in data) if (data[k] != null) payload[k] = data[k];
        }
        fetch(apiUrl("/widget/lead"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          keepalive: true,
        }).catch(function () {});
      } catch (e) {}
      return window.OraOne;
    };
    _sdkImpl.trackPurchase = function (data) {
      postEvent("purchase", data || {});
      return window.OraOne;
    };
    _sdkImpl.openChat = function () {
      if (loaded) setOpen(true);
      else pendingOpen = true;
      return window.OraOne;
    };
    // startChat([message]) — open the panel and optionally prefill/send a
    // first message so buttons like "Talk to sales" land in a conversation.
    _sdkImpl.startChat = function (message) {
      if (loaded) setOpen(true);
      else pendingOpen = true;
      if (message != null && String(message).trim()) {
        var text = String(message);
        var deliver = function () {
          try {
            iframe.contentWindow.postMessage(
              { source: "oraone-host", type: "prefill", text: text, send: true },
              "*"
            );
          } catch (e) {}
        };
        if (loaded) deliver();
        else pendingPrefill = deliver;
      }
      return window.OraOne;
    };
    _sdkImpl.closeChat = function () {
      setOpen(false);
      return window.OraOne;
    };
    _sdkImpl.toggleChat = function () {
      setOpen(!open);
      return window.OraOne;
    };
    // Short aliases mandated by the public SDK surface.
    _sdkImpl.open = _sdkImpl.openChat;
    _sdkImpl.close = _sdkImpl.closeChat;
    _sdkImpl.toggle = _sdkImpl.toggleChat;
    _sdkImpl.trackEvent = _sdkImpl.sendEvent;
    // init(options) — idempotent boot hook. The widget already auto-inits from
    // data-widget-id; init() lets SDK users pass identity/context/theme and
    // optionally auto-open. Safe to call repeatedly.
    _sdkImpl.init = function (options) {
      options = options || {};
      if (options.user || options.identify) mergeContext(options.user || options.identify);
      if (options.context) mergeContext(options.context);
      if (options.autoOpen) {
        if (loaded) setOpen(true);
        else pendingOpen = true;
      }
      return window.OraOne;
    };

    _sdkReady = true;
    var q = _sdkQueue.splice(0, _sdkQueue.length);
    q.forEach(function (call) {
      var m = call[0];
      if (_sdkImpl[m]) {
        try {
          _sdkImpl[m].apply(null, call[1]);
        } catch (e) {}
      }
    });
  }

  // ---- Self-contained chat app rendered inside the iframe ----------------------
  // Optional developer style overrides for the in-iframe chat UI. Read from a
  // `data-css` selector on the loader script (pointing at an inert element such
  // as <script type="text/oraone-css">…</script>) or window.OraOneWidget.customCSS.
  // Injected AFTER the base styles so it wins, letting developers fully restyle
  // the widget (.hd header, .bd body, .msg.a / .msg.u bubbles, .ft footer, .row
  // input, .send button, .lead form, …) without forking the SDK.
  function readCustomCSS() {
    var css = "";
    try {
      var sel = script.getAttribute("data-css");
      if (sel) {
        var el = document.querySelector(sel);
        if (el && el.textContent) css += el.textContent;
      }
    } catch (e) {}
    try {
      var w = window.OraOneWidget;
      if (w && typeof w.customCSS === "string") css += "\n" + w.customCSS;
    } catch (e) {}
    return css;
  }

  function buildAppHtml() {
    var endTag = "</" + "script>";
    return (
      "<!doctype html><html><head><meta charset='utf-8'>" +
      "<meta name='viewport' content='width=device-width,initial-scale=1'>" +
      "<style>" + APP_CSS + readCustomCSS() + "</style></head><body>" +
      "<div id='root'></div>" +
      "<script>" + APP_JS + endTag +
      "</body></html>"
    );
  }

  var APP_CSS =
    "*{box-sizing:border-box}html,body{margin:0;height:100%;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}" +
    "#root{display:flex;flex-direction:column;height:100%;background:var(--bg,#fff);color:var(--text,#0f172a)}" +
    ".hd{display:flex;align-items:center;gap:10px;padding:14px 16px;background:var(--primary,#2563EB);color:#fff}" +
    ".hd .av{width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,.22);display:flex;align-items:center;justify-content:center;font-weight:700;overflow:hidden}" +
    ".hd .av img{width:100%;height:100%;object-fit:cover}" +
    ".hd .ti{font-weight:600;font-size:15px;line-height:1.1}.hd .sub{font-size:12px;opacity:.85}" +
    ".hd .x{margin-left:auto;background:none;border:0;color:#fff;cursor:pointer;font-size:20px;opacity:.85;line-height:1}" +
    ".bd{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;background:var(--bg,#fff)}" +
    ".msg{max-width:84%;padding:10px 13px;border-radius:14px;font-size:14px;line-height:1.45;white-space:pre-wrap;word-wrap:break-word}" +
    ".msg.a{align-self:flex-start;background:#f1f5f9;color:#0f172a;border-bottom-left-radius:4px}" +
    ".msg.u{align-self:flex-end;background:var(--primary,#2563EB);color:#fff;border-bottom-right-radius:4px}" +
    ".src{align-self:flex-start;max-width:84%;font-size:11px;color:#64748b;margin-top:-6px}" +
    ".src a{color:var(--primary,#2563EB);text-decoration:none}.src a:hover{text-decoration:underline}" +
    ".sug{display:flex;flex-wrap:wrap;gap:8px;margin-top:4px}" +
    ".sug button{font-size:12.5px;padding:7px 11px;border-radius:14px;border:1px solid #e2e8f0;background:#fff;color:#334155;cursor:pointer}" +
    ".sug button:hover{border-color:var(--primary,#2563EB);color:var(--primary,#2563EB)}" +
    ".typing{display:flex;gap:4px;align-self:flex-start;padding:12px 14px;background:#f1f5f9;border-radius:14px}" +
    ".typing span{width:7px;height:7px;border-radius:50%;background:#94a3b8;animation:b 1s infinite}" +
    ".typing span:nth-child(2){animation-delay:.15s}.typing span:nth-child(3){animation-delay:.3s}" +
    "@keyframes b{0%,80%,100%{opacity:.3}40%{opacity:1}}" +
    ".tb{display:flex;gap:6px;margin-top:2px}.tb button{background:none;border:0;cursor:pointer;font-size:14px;opacity:.55}.tb button:hover{opacity:1}" +
    ".ft{border-top:1px solid #eef2f7;padding:10px;background:#fff}" +
    ".row{display:flex;gap:8px;align-items:flex-end}" +
    ".row textarea{flex:1;resize:none;border:1px solid #e2e8f0;border-radius:12px;padding:10px 12px;font-size:14px;font-family:inherit;max-height:90px;outline:none}" +
    ".row textarea:focus{border-color:var(--primary,#2563EB)}" +
    ".row .send{width:40px;height:40px;border-radius:50%;border:0;background:var(--primary,#2563EB);color:#fff;cursor:pointer;flex:0 0 auto;display:flex;align-items:center;justify-content:center}" +
    ".row .send:disabled{opacity:.5;cursor:default}" +
    ".brand{text-align:center;font-size:11px;color:#94a3b8;padding:6px 0 2px}.brand a{color:#94a3b8;text-decoration:none}" +
    ".esc{text-align:center;margin:4px 0}.esc button{font-size:12px;color:#64748b;background:none;border:0;cursor:pointer;text-decoration:underline}" +
    ".lead{display:flex;flex-direction:column;gap:8px;background:#f8fafc;border:1px solid #eef2f7;border-radius:12px;padding:12px;align-self:stretch}" +
    ".lead input{border:1px solid #e2e8f0;border-radius:9px;padding:9px 11px;font-size:13px;outline:none}" +
    ".lead button{background:var(--primary,#2563EB);color:#fff;border:0;border-radius:9px;padding:9px;font-size:13px;font-weight:600;cursor:pointer}" +
    ".lead .t{font-size:13px;font-weight:600}";

  // The in-iframe app. Kept as a string so it can be injected via srcdoc.
  var APP_JS = [
    "(function(){",
    "var S={api:null,key:null,visitor:null,cfg:null,ctx:{},session:null,busy:false,leadShown:false};",
    "function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}",
    "function $(h){var t=document.createElement('template');t.innerHTML=h.trim();return t.content.firstChild;}",
    "var root=document.getElementById('root');",
    "function send(type,extra){var m={source:'oraone-app',type:type};if(extra)for(var k in extra)m[k]=extra[k];parent.postMessage(m,'*');}",
    "function api(path,body){return fetch(S.api+'/api'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json().then(function(j){return{ok:r.ok,status:r.status,data:j};});});}",
    // build shell
    "function build(){",
    "var t=S.cfg.theme||{},st=S.cfg.settings||{};",
    "root.style.setProperty('--primary',t.primary_color||'#2563EB');",
    "root.style.setProperty('--bg',t.background_color||'#fff');",
    "root.style.setProperty('--text',t.text_color||'#0f172a');",
    "var name=st.agent_name||S.cfg.agent_name||'Assistant';",
    "var av=t.avatar_url?(\"<img src='\"+esc(t.avatar_url)+\"' alt=''>\"):esc(name.slice(0,1).toUpperCase());",
    "var hd=$(\"<div class='hd'><div class='av'>\"+av+\"</div><div><div class='ti'>\"+esc(name)+\"</div><div class='sub'>\"+esc(st.company_name||'Online')+\"</div></div><button class='x' aria-label='Close'>&times;</button></div>\");",
    "hd.querySelector('.x').onclick=function(){send('close');};",
    "root.appendChild(hd);",
    "S.body=$(\"<div class='bd'></div>\");root.appendChild(S.body);",
    "var ft=$(\"<div class='ft'></div>\");",
    "var row=$(\"<div class='row'><textarea rows='1' placeholder=\\\"\"+esc(st.input_placeholder||'Ask a question…')+\"\\\"></textarea><button class='send' aria-label='Send'><svg width='18' height='18' viewBox='0 0 24 24' fill='none'><path d='M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z' stroke='#fff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg></button></div>\");",
    "S.input=row.querySelector('textarea');S.sendBtn=row.querySelector('.send');",
    "S.input.addEventListener('input',function(){S.input.style.height='auto';S.input.style.height=Math.min(S.input.scrollHeight,90)+'px';});",
    "S.input.addEventListener('keydown',function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();submit();}});",
    "S.sendBtn.onclick=submit;ft.appendChild(row);",
    "if(st.enable_escalation){var esc2=$(\"<div class='esc'><button>Talk to a human</button></div>\");esc2.querySelector('button').onclick=escalate;ft.appendChild(esc2);}",
    "if(st.show_branding){ft.appendChild($(\"<div class='brand'>Powered by <a href='https://oraone.in' target='_blank' rel='noopener'>OraOne</a></div>\"));}",
    "root.appendChild(ft);",
    "}",
    // append helpers
    "function scrollDown(){S.body.scrollTop=S.body.scrollHeight;}",
    "function addUser(text){S.body.appendChild($(\"<div class='msg u'>\"+esc(text)+\"</div>\"));scrollDown();}",
    "function addAgent(text){var el=$(\"<div class='msg a'>\"+esc(text)+\"</div>\");S.body.appendChild(el);scrollDown();return el;}",
    "function addSources(sources){if(!sources||!sources.length)return;var parts=[];for(var i=0;i<sources.length;i++){var s=sources[i];var label=esc(s.title||('Source '+(i+1)));if(s.url){parts.push(\"<a href='\"+esc(s.url)+\"' target='_blank' rel='noopener'>\"+label+\"</a>\");}else{parts.push(label);}}S.body.appendChild($(\"<div class='src'>Sources: \"+parts.join(' · ')+\"</div>\"));scrollDown();}",
    "function feedback(messageId,el){if(!messageId)return;var tb=$(\"<div class='tb'><button title='Helpful'>&#128077;</button><button title='Not helpful'>&#128078;</button></div>\");var btns=tb.querySelectorAll('button');function rate(v){return function(){api('/widget/feedback',{public_key:S.key,visitor_id:S.visitor,session_id:S.session,message_id:messageId,rating:v});tb.innerHTML=\"<span style='font-size:12px;color:#94a3b8'>Thanks for the feedback</span>\";};}btns[0].onclick=rate(5);btns[1].onclick=rate(1);el.appendChild(tb);}",
    "function typing(on){if(on){S.typing=$(\"<div class='typing'><span></span><span></span><span></span></div>\");S.body.appendChild(S.typing);scrollDown();}else if(S.typing){S.typing.remove();S.typing=null;}}",
    // suggested questions
    "function suggestions(){var st=S.cfg.settings||{};var q=st.suggested_questions||[];if(!q.length)return;var wrap=$(\"<div class='sug'></div>\");q.forEach(function(text){var b=document.createElement('button');b.textContent=text;b.onclick=function(){wrap.remove();ask(text);};wrap.appendChild(b);});S.body.appendChild(wrap);scrollDown();}",
    // lead capture
    "function maybeLead(){var st=S.cfg.settings||{};if(!st.collect_leads||S.leadShown)return;S.leadShown=true;var fields=st.lead_fields||['name','email'];var form=$(\"<div class='lead'><div class='t'>Leave your details and we'll follow up</div></div>\");var inputs={};fields.forEach(function(f){var inp=document.createElement('input');inp.placeholder=f.charAt(0).toUpperCase()+f.slice(1);inp.type=f==='email'?'email':(f==='phone'?'tel':'text');inputs[f]=inp;form.appendChild(inp);});var btn=document.createElement('button');btn.textContent='Submit';btn.onclick=function(){var payload={public_key:S.key,visitor_id:S.visitor,session_id:S.session};for(var f in inputs)payload[f]=inputs[f].value;api('/widget/lead',payload).then(function(){form.innerHTML=\"<div class='t'>Thanks! We'll be in touch.</div>\";});};form.appendChild(btn);S.body.appendChild(form);scrollDown();}",
    "function escalate(){api('/widget/escalate',{public_key:S.key,visitor_id:S.visitor,session_id:S.session,reason:'user_requested'}).then(function(){addAgent('A team member has been notified and will follow up shortly.');maybeLead();});send('event',{event:'escalation',metadata:{}});}",
    // ask flow
    "function submit(){var v=(S.input.value||'').trim();if(!v)return;S.input.value='';S.input.style.height='auto';ask(v);}",
    "function ask(text){if(S.busy)return;S.busy=true;S.sendBtn.disabled=true;addUser(text);typing(true);",
    "api('/widget/chat',{public_key:S.key,visitor_id:S.visitor,session_id:S.session,message:text,user_context:S.ctx}).then(function(r){typing(false);S.busy=false;S.sendBtn.disabled=false;",
    "if(!r.ok){addAgent(r.status===429?'You are sending messages too quickly. Please wait a moment.':'Sorry, something went wrong. Please try again.');return;}",
    "var d=r.data;if(d.session_id)S.session=d.session_id;var el=addAgent(d.answer||'');addSources(d.sources);feedback(d.message_id,el);",
    "if(d.related_questions&&d.related_questions.length){var wrap=$(\"<div class='sug'></div>\");d.related_questions.slice(0,3).forEach(function(q){var b=document.createElement('button');b.textContent=q;b.onclick=function(){wrap.remove();ask(q);};wrap.appendChild(b);});S.body.appendChild(wrap);scrollDown();}",
    "S.turns=(S.turns||0)+1;if(S.turns>=2)maybeLead();",
    "}).catch(function(){typing(false);S.busy=false;S.sendBtn.disabled=false;addAgent('Sorry, something went wrong. Please try again.');});}",
    // session restore
    "function startSession(){api('/widget/session',{public_key:S.key,visitor_id:S.visitor,user_context:S.ctx}).then(function(r){if(r.ok&&r.data){S.session=r.data.session_id;var msgs=r.data.messages||[];if(msgs.length){msgs.forEach(function(m){if(m.role==='user'||m.sender==='customer')addUser(m.content||m.message||'');else addAgent(m.content||m.message||'');});return;}}greet();}).catch(greet);}",
    "function greet(){var st=S.cfg.settings||{};addAgent(st.welcome_message||'Hi! How can I help you today?');suggestions();}",
    // init from host
    "window.addEventListener('message',function(ev){var d=ev.data;if(!d||d.source!=='oraone-host')return;if(d.type==='init'){var p=d.payload;S.api=p.apiBase;S.key=p.widgetId;S.visitor=p.visitorId;S.cfg=p.config;S.ctx=p.context||{};build();startSession();}else if(d.type==='context'){if(d.payload&&typeof d.payload==='object'){for(var ck in d.payload)S.ctx[ck]=d.payload[ck];}}else if(d.type==='prefill'){if(S.input){S.input.value=d.text||'';}if(d.send&&d.text){ask(d.text);}}else if(d.type==='focus'){if(S.input)S.input.focus();}});",
    "send('ready');",
    "})();",
  ].join("\n");
})();
