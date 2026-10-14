// Real-backend route audit: signs in with the local QA account (password + OTP
// read from the local backend cache), visits every reference destination and
// records final URL, heading, state classification, console/page errors,
// 5xx API responses and axe-core WCAG A/AA violations.
// Usage: BASE_URL=https://... ORAONE_LOCAL_TEST_PASSWORD=... node e2e/real-route-audit.mjs
import { chromium } from "@playwright/test";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const routes = require("./route-inventory.json");
const axeSource = fs.readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const BASE = process.env.BASE_URL;
const EMAIL = "test@oraone.in";
const PASSWORD = process.env.ORAONE_LOCAL_TEST_PASSWORD;
const VIEWPORT = { width: Number(process.env.VW || 1440), height: Number(process.env.VH || 900) };
const AXE = process.env.AXE !== "0";
if (!BASE || !PASSWORD) throw new Error("Set BASE_URL and ORAONE_LOCAL_TEST_PASSWORD.");

const backend = path.resolve(process.cwd(), "../backend");
const readOtp = () =>
  execFileSync(
    "python",
    ["-c", `from app.services import auth_service as a; print(a._cache().get(a._login_otp_key("${EMAIL}")) or "")`],
    { cwd: backend, encoding: "utf8" },
  ).trim();

const sample = (p) =>
  p.replace(/\$[A-Za-z]+/g, "00000000-0000-4000-8000-000000000999");

function classify(finalPath, text, requested) {
  const t = text.toLowerCase();
  if (finalPath !== requested.split("?")[0]) return "alias-redirect";
  if (/page not found|404/.test(t) && /not found/.test(t)) return "not-found";
  if (/(access denied|not authorized|permission|restricted|super admin only|platform admin)/.test(t) && /(denied|restricted|not authorized|only)/.test(t)) return "restricted";
  if (/(design preview|preview only|planned product|coming soon|not yet available|on the roadmap|planned)/.test(t)) return "preview-or-planned";
  if (/(unavailable|could not load|failed to load|try again)/.test(t)) return "functional-unavailable-state";
  return "functional";
}

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: VIEWPORT });
const page = await context.newPage();
await page.addInitScript(() => localStorage.setItem("oraone_tour_seen_v1", "1"));

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.getByTestId("login-email-input").fill(EMAIL);
await page.getByTestId("login-password-input").fill(PASSWORD);
await page.getByTestId("login-submit").click();
await page.getByTestId("login-otp-form").waitFor({ timeout: 20000 });
const otp = readOtp();
const boxes = page.getByTestId("login-otp-input").locator("input");
if ((await boxes.count()) > 1) {
  for (let i = 0; i < otp.length; i++) await boxes.nth(i).fill(otp[i]);
} else {
  await boxes.first().fill(otp);
}
await page.getByTestId("login-otp-submit").click();
await page.waitForURL((u) => !u.pathname.startsWith("/login"), { timeout: 30000 });
console.log("Signed in; landed on", new URL(page.url()).pathname);

const results = [];
const only = process.env.ONLY ? new RegExp(process.env.ONLY) : null;
for (const r of routes.filter((x) => x.type !== "layout" && (!only || only.test(x.path)))) {
  const requested = sample(r.path);
  const consoleErrors = [];
  const serverErrors = [];
  const onConsole = (m) => m.type() === "error" && consoleErrors.push(m.text().slice(0, 200));
  const onPageError = (e) => consoleErrors.push("pageerror: " + e.message.slice(0, 200));
  const onResponse = (res) => {
    if (res.url().includes("/api/") && res.status() >= 500) serverErrors.push(`${res.status()} ${new URL(res.url()).pathname}`);
  };
  page.on("console", onConsole);
  page.on("pageerror", onPageError);
  page.on("response", onResponse);
  let status = "ok";
  try {
    await page.goto(BASE + requested, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForLoadState("networkidle", { timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(1200);
  } catch (e) {
    status = "timeout";
  }
  const finalPath = new URL(page.url()).pathname;
  const heading = (await page.locator("h1").first().textContent({ timeout: 1000 }).catch(() => "")) || "";
  const scope = (await page.locator("main").count()) ? page.locator("main").first() : page.locator("body");
  const text = (await scope.innerText().catch(() => "")).slice(0, 4000);
  let axe = null;
  if (AXE) {
    await page.addScriptTag({ content: axeSource }).catch(() => {});
    axe = await page
      .evaluate(async () => {
        const res = await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"] } });
        return res.violations
          .filter((v) => ["critical", "serious"].includes(v.impact))
          .map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length, targets: v.nodes.slice(0, 4).map((n) => n.target.join(" ") + " :: " + (n.failureSummary || "").split("\n").slice(-1)[0].slice(0, 160)) }));
      })
      .catch(() => null);
  }
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1).catch(() => null);
  page.off("console", onConsole);
  page.off("pageerror", onPageError);
  page.off("response", onResponse);
  const entry = {
    path: r.path,
    requested,
    finalPath,
    navStatus: status,
    heading: heading.trim().slice(0, 80),
    classification: finalPath.startsWith("/login") ? "auth-required" : classify(finalPath, text, requested),
    serverErrors,
    consoleErrors: consoleErrors.slice(0, 3),
    axe,
    horizontalOverflow: overflow,
  };
  results.push(entry);
  console.log(`${entry.classification.padEnd(28)} ${r.path} -> ${finalPath} ${serverErrors.length ? "5xx:" + serverErrors.length : ""} ${axe && axe.length ? "axe:" + axe.map((v) => v.id).join(",") : ""}${overflow ? " OVERFLOW" : ""}`);
}
await browser.close();
const out = path.resolve(process.cwd(), `output/real-route-audit-${VIEWPORT.width}.json`);
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(results, null, 2));
console.log("Wrote", out, results.length, "destinations");
