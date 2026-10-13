import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

const require = createRequire(import.meta.url);

test("SDK remains SSR-safe and replays calls queued before the async loader is ready", async (t) => {
  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;
  const previousOraOne = globalThis.OraOne;
  t.after(() => {
    if (previousWindow === undefined) delete globalThis.window;
    else globalThis.window = previousWindow;
    if (previousDocument === undefined) delete globalThis.document;
    else globalThis.document = previousDocument;
    if (previousOraOne === undefined) delete globalThis.OraOne;
    else globalThis.OraOne = previousOraOne;
  });

  delete globalThis.window;
  delete globalThis.document;
  const { OraOne: serverSdk } = await import(
    `../src/index.js?ssr=${Date.now()}`
  );
  assert.equal(serverSdk.init(), serverSdk);
  assert.equal(serverSdk.startChat("SSR-safe"), serverSdk);

  const listeners = new Map();
  const attributes = new Map();
  const script = {
    async: false,
    src: "",
    addEventListener(name, callback) {
      listeners.set(name, callback);
    },
    setAttribute(name, value) {
      attributes.set(name, value);
    },
  };
  const appended = [];
  globalThis.window = {};
  globalThis.document = {
    querySelector: () => appended[0] || null,
    createElement: (tag) => {
      assert.equal(tag, "script");
      return script;
    },
    head: { appendChild: (element) => appended.push(element) },
  };

  const { OraOne: browserSdk } = await import(
    `../src/index.js?browser=${Date.now()}`
  );
  browserSdk.init({
    agentId: "wgt_public_example",
    apiBase: "https://api.example.test",
    user: { email: "visitor@example.test" },
    context: { page: "/pricing" },
    autoOpen: true,
  });
  browserSdk.trackEvent("pricing_viewed", { plan: "free" });

  assert.equal(appended.length, 1);
  assert.equal(script.src, "https://oraone.in/widget.js");
  assert.equal(script.async, true);
  assert.equal(attributes.get("data-widget-id"), "wgt_public_example");
  assert.equal(attributes.get("data-api"), "https://api.example.test");
  assert.equal(attributes.get("data-oraone-loader"), "1");
  assert.equal(typeof listeners.get("load"), "function");

  const calls = [];
  globalThis.window.OraOne = Object.fromEntries(
    ["identifyUser", "updateContext", "open", "init", "trackEvent"].map(
      (method) => [method, (...args) => calls.push([method, ...args])],
    ),
  );
  listeners.get("load")();

  assert.deepEqual(
    calls.map(([method]) => method),
    ["identifyUser", "updateContext", "open", "init", "trackEvent"],
  );
  assert.deepEqual(calls[0][1], { email: "visitor@example.test" });
  assert.deepEqual(calls[1][1], { page: "/pricing" });
  assert.deepEqual(calls[4][1], "pricing_viewed");

  const commonJs = require("../dist/index.cjs");
  assert.equal(commonJs, commonJs.OraOne);
  globalThis.window.OraOne = undefined;
  commonJs.init({ agentId: "wgt_commonjs_example" });
  commonJs.identifyUser({ name: "Visitor" });
  globalThis.window.OraOne = {
    init: (...args) => calls.push(["commonjs-init", ...args]),
    identifyUser: (...args) => calls.push(["commonjs-identify", ...args]),
  };
  listeners.get("load")();
  assert.deepEqual(
    calls.slice(-2).map(([method]) => method),
    ["commonjs-init", "commonjs-identify"],
  );
  assert.deepEqual(calls.at(-1), ["commonjs-identify", { name: "Visitor" }]);
});
