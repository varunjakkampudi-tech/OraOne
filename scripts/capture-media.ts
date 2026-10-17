/**
 * Captures product screenshots and a short widget demo video from the running app.
 *
 * Usage (app and API running locally, example assistant already created):
 *   bun scripts/capture-media.ts <assistantId>
 *
 * Output goes to public/media. The media shows the real product with example content;
 * re-capture it from the production site before launch.
 */
import { mkdirSync, renameSync, readdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";
import { chromium, type BrowserContext, type Page } from "@playwright/test";

const APP = process.env["E2E_BASE_URL"] ?? "http://localhost:5180";
const API = process.env["API_URL"] ?? "http://localhost:8000";
const [assistantId] = process.argv.slice(2);
if (!assistantId) {
  console.error("usage: bun scripts/capture-media.ts <assistantId>");
  process.exit(1);
}
const DEV_EMAIL = process.env["E2E_DEV_EMAIL"] ?? "";
const DEV_PASSWORD = process.env["E2E_DEV_PASSWORD"] ?? "";
if (!DEV_EMAIL || !DEV_PASSWORD) {
  console.error("Set E2E_DEV_EMAIL and E2E_DEV_PASSWORD for a seeded local development account.");
  process.exit(1);
}
const OUT = resolve(import.meta.dirname, "../public/media");
mkdirSync(OUT, { recursive: true });

async function signIn(context: BrowserContext) {
  const res = await context.request.post(`${APP}/api/auth/dev-login`, {
    data: { email: DEV_EMAIL, password: DEV_PASSWORD },
  });
  if (res.status() !== 200) throw new Error(`dev-login failed: ${res.status()}`);
}

async function projectId(context: BrowserContext): Promise<string> {
  const res = await context.request.get(`${APP}/api/projects?limit=5`);
  return (await res.json()).items[0].id as string;
}

async function shot(page: Page, name: string) {
  await page.waitForTimeout(800);
  await page.screenshot({ path: resolve(OUT, `${name}.jpg`), type: "jpeg", quality: 86 });
  console.log("shot", name);
}

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 1,
  });
  await signIn(context);
  const pid = await projectId(context);
  const page = await context.newPage();

  // A published widget for the example assistant, so the host page can embed it.
  const widget = await context.request.post(`${API}/api/widgets`, {
    headers: { "X-Project-Id": pid },
    data: {
      name: "Example clinic website chat",
      agent_id: assistantId,
      domains: [],
      widget_type: "bubble",
      position: "bottom-right",
      auth_mode: "public",
    },
  });
  const widgetData = widget.status() === 201 ? await widget.json() : null;
  const widgetId =
    widgetData?.id ??
    (
      await (
        await context.request.get(`${API}/api/widgets?limit=100`, {
          headers: { "X-Project-Id": pid },
        })
      ).json()
    ).items.find((w: { agent_id: string }) => w.agent_id === assistantId).id;
  await context.request.post(`${API}/api/widgets/${widgetId}/publish?publish=true`);
  const publicKey =
    (await (await context.request.get(`${API}/api/widgets/${widgetId}`)).json()).public_key ??
    widgetData?.public_key;
  console.log("widget published", publicKey);

  // Studio screens.
  await page.goto(`${APP}/studio`);
  await page.getByRole("heading", { name: "Your assistants" }).waitFor();
  await shot(page, "studio-assistants");

  await page.goto(`${APP}/studio/assistants/${assistantId}`);
  await page.getByRole("heading", { name: "Example clinic assistant" }).waitFor();
  await shot(page, "studio-assistant-editor");

  await page.goto(`${APP}/studio/knowledge`);
  await page.getByRole("heading", { name: "Knowledge" }).waitFor();
  await shot(page, "studio-knowledge");

  await page.goto(`${APP}/studio/inbox`);
  await page.getByRole("heading", { name: "Conversations" }).waitFor();
  await shot(page, "studio-inbox");

  await page.goto(`${APP}/studio/assistants/${assistantId}/install`);
  await page.getByRole("heading", { name: /Add .* to your website/ }).waitFor();
  await shot(page, "studio-install");

  await page.goto(`${APP}/studio/leads`);
  await page.getByRole("heading", { name: "Leads" }).waitFor();
  await shot(page, "studio-leads");

  await page.close();

  // Widget demo: a visitor opens the chat on the example website and asks a question.
  const videoDir = resolve(OUT, "_video");
  rmSync(videoDir, { recursive: true, force: true });
  const demo = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: videoDir, size: { width: 1280, height: 720 } },
  });
  // A simple example website that embeds the widget with a single script tag.
  const hostPath = resolve(OUT, "_demo-host.html");
  await Bun.write(
    hostPath,
    `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Example clinic</title>
<style>body{font-family:Inter,system-ui,sans-serif;margin:0;background:#f8fafc;color:#0f172a}
header{padding:20px 40px;border-bottom:1px solid #e2e8f0;font-weight:600}
main{padding:56px 40px;max-width:720px}h1{font-size:34px;margin:0 0 12px}p{font-size:18px;line-height:1.6;color:#475569}</style>
</head><body><header>Example clinic</header><main><h1>Welcome to our clinic</h1>
<p>Book a check-up, ask about treatments or find our opening hours.</p></main>
<script src="${APP}/widget.js" data-widget-id="${publicKey}" data-api="${API}" async></script>
</body></html>`,
  );
  const visitor = await demo.newPage();
  await visitor.goto(`${APP}/media/_demo-host.html`);
  await visitor.waitForTimeout(2500);
  await visitor.evaluate(() =>
    (window as unknown as { OraOne: { open: () => void } }).OraOne?.open(),
  );
  await visitor.waitForTimeout(1500);
  await visitor.evaluate(() =>
    (window as unknown as { OraOne: { send: (t: string) => void } }).OraOne?.send(
      "Are you open on Saturday?",
    ),
  );
  await visitor.waitForTimeout(9000);
  await visitor.evaluate(() =>
    (window as unknown as { OraOne: { send: (t: string) => void } }).OraOne?.send(
      "How do I book an appointment?",
    ),
  );
  await visitor.waitForTimeout(9000);
  await demo.close();
  const recorded = readdirSync(videoDir).find((f) => f.endsWith(".webm"));
  if (recorded) renameSync(resolve(videoDir, recorded), resolve(OUT, "widget-demo.webm"));
  rmSync(videoDir, { recursive: true, force: true });
  console.log("video widget-demo.webm");

  rmSync(hostPath, { force: true });
  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
