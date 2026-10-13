/* Real local UI verification: no API mocks, persisted synthetic resources only. */
const { chromium, expect } = require("@playwright/test");
const { randomBytes } = require("node:crypto");
const { execFileSync } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const backend = path.resolve(__dirname, "../../backend");
const python = path.join(
  backend,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const base = process.env.ORAONE_LOCAL_UI_URL || "http://localhost:3001";
if (!["localhost", "127.0.0.1"].includes(new URL(base).hostname))
  throw new Error("Local UI only");
const email = `oraone-local-e2e-${randomBytes(16).toString("hex")}@example.com`;
const password = `Aa1!${randomBytes(24).toString("base64url")}`;
const output = path.resolve(__dirname, "../output/playwright/live-local");
fs.mkdirSync(output, { recursive: true });
const outcomes = [];
const errors = [];
const failedRequests = [];
const codeFor = (kind) =>
  execFileSync(
    python,
    [
      "-c",
      "import sys; from app.core.config import settings; from app.services import auth_service as a; assert settings.environment == 'development'; f={'verify':a._verify_code_key,'login':a._login_otp_key,'reset':a._reset_code_key}[sys.argv[1]]; c=a._cache().get(f(sys.argv[2])); assert c; print(c)",
      kind,
      email,
    ],
    { cwd: backend, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
  ).trim();

async function digits(page, id, code) {
  if (!/^\d{6}$/.test(code)) throw new Error("Local OTP retrieval failed");
  for (const [i, value] of [...code].entries())
    await page
      .getByTestId(id)
      .getByLabel(`Digit ${i + 1}`)
      .fill(value);
}

(async () => {
  let browser;
  let page;
  try {
    browser = await chromium.launch();
    const context = await browser.newContext({
      viewport: { width: 1440, height: 960 },
    });
    page = await context.newPage();
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("response", (response) => {
      if (response.status() >= 400)
        failedRequests.push({
          path: new URL(response.url()).pathname,
          status: response.status(),
        });
    });
    page.on("requestfailed", (request) =>
      failedRequests.push({
        path: new URL(request.url()).pathname,
        error: request.failure().errorText,
      }),
    );
    await page.addInitScript(() =>
      localStorage.setItem("oraone_tour_seen_v1", "1"),
    );
    await page.goto(`${base}/signup`);
    await page.getByTestId("signup-name-input").fill("Local UI verification");
    await page.getByTestId("signup-email-input").fill(email);
    await page.getByTestId("signup-password-input").fill(password);
    await page.getByTestId("signup-confirm-input").fill(password);
    await page.getByTestId("signup-terms").check({ force: true });
    let signupResponse = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/auth/signup") && r.request().method() === "POST",
    );
    await page.getByTestId("signup-submit").click();
    let signupResult = await signupResponse;
    if (signupResult.status() === 429) {
      await page.waitForTimeout(
        Math.min(
          60000,
          Math.max(
            1000,
            Number(signupResult.headers()["retry-after"] || 60) * 1000,
          ),
        ),
      );
      signupResponse = page.waitForResponse(
        (r) =>
          r.url().endsWith("/api/auth/signup") &&
          r.request().method() === "POST",
      );
      await page.getByTestId("signup-submit").click();
      signupResult = await signupResponse;
    }
    expect(signupResult.status()).toBe(200);
    await expect(page).toHaveURL(/\/verify-email$/);
    await digits(page, "verify-code-input", codeFor("verify"));
    await page.getByTestId("verify-submit").click();
    await expect(page).toHaveURL(/\/login$/, { timeout: 30000 });
    await page.getByTestId("login-email-input").fill(email);
    await page.getByTestId("login-password-input").fill(password);
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-otp-form")).toBeVisible({
      timeout: 30000,
    });
    await digits(page, "login-otp-input", codeFor("login"));
    await page.getByTestId("login-otp-submit").click();
    await expect(page).toHaveURL(/\/app\/dashboard$/, { timeout: 30000 });
    outcomes.push("Real signup, verification and password/OTP login");

    await page.goto(`${base}/app/projects`);
    await page.getByTestId("new-project-btn").click();
    await page.getByTestId("project-name-input").fill("Local UI project");
    const projectCreation = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/projects") && r.request().method() === "POST",
    );
    await page.getByTestId("project-save-btn").click();
    expect((await projectCreation).status()).toBe(201);
    await expect(page.getByTestId("project-modal")).toHaveCount(0, {
      timeout: 15000,
    });
    await page.reload();
    await expect(
      page.getByText("Local UI project", { exact: true }),
    ).toBeVisible();
    outcomes.push("Project creation persisted across reload");

    await page.goto(`${base}/app/knowledge-base`);
    await page.getByTestId("kb-empty-create-btn").click();
    await page.getByTestId("kb-create-name").fill("Local UI knowledge");
    await page.getByTestId("kb-create-status").selectOption("active");
    const created = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/knowledge-bases") &&
        r.request().method() === "POST",
    );
    await page.getByTestId("kb-create-submit").click();
    const response = await created;
    expect(response.status()).toBe(201);
    const kb = await response.json();
    await page.getByTestId(`kb-open-${kb.id}`).click();
    await page.getByTestId("kb-details-file-input").setInputFiles({
      name: "local-ui-facts.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("Local UI verification document: PINEAPPLE-42."),
    });
    await expect(
      page.getByText("local-ui-facts.txt", { exact: true }),
    ).toBeVisible({ timeout: 30000 });
    outcomes.push("Knowledge creation and real document upload");
    const fixtures = await page.evaluate(
      async ({ kbId, email }) => {
        const { api } = await import("/src/lib/api.js");
        const { data: agent } = await api.post("/agents", {
          name: "Local UI assistant",
          type: "chat",
          model: "openrouter/free",
          system_prompt:
            "Use the connected business knowledge to answer clearly.",
          knowledge_base_ids: [kbId],
        });
        const { data: lead } = await api.post("/leads", {
          name: "Local UI contact",
          email,
          company: "Local verification",
        });
        return { agentId: agent.id, leadId: lead.id };
      },
      { kbId: kb.id, email },
    );

    for (const route of [
      "dashboard",
      "agents",
      "conversations",
      "leads",
      "analytics",
      "knowledge-base",
      "integrations",
      "widgets",
      "team",
      "usage",
      "settings",
      "products/chat",
      "products/chat/knowledge/documents",
    ]) {
      // Full document navigation rehydrates the shell; respect real API limits.
      await page.waitForTimeout(12000);
      await page.goto(`${base}/app/${route}`);
      await expect(page).toHaveURL(new RegExp(`/app/${route}$`));
      await page
        .locator(
          '[data-testid="profile-menu"], [data-testid="session-verification-error"], [data-testid="protected-route-identity-error"]',
        )
        .first()
        .waitFor({ state: "visible", timeout: 15000 });
      if (await page.getByTestId("session-verification-error").isVisible()) {
        await page.waitForTimeout(60000);
        await page.getByTestId("session-verification-retry").click();
        outcomes.push("Real session retry recovered after rate limiting");
      } else if (
        await page.getByTestId("protected-route-identity-error").isVisible()
      ) {
        await page.waitForTimeout(60000);
        await page.getByTestId("protected-route-identity-retry").click();
        outcomes.push("Real workspace retry recovered after rate limiting");
      }
      await expect(page.getByTestId("profile-menu")).toBeVisible({
        timeout: 15000,
      });
      await expect(page.locator("main").first()).toBeVisible();
      await expect(page.getByTestId("oraone-loader")).toHaveCount(0, {
        timeout: 15000,
      });
      await expect(page.getByTestId("error-boundary-screen")).toHaveCount(0);
      await expect(page.locator('main [aria-busy="true"]')).toHaveCount(0, {
        timeout: 30000,
      });
      await expect(
        page.locator('main [aria-hidden="true"].animate-pulse'),
      ).toHaveCount(0, { timeout: 30000 });
      await page.screenshot({
        path: path.join(output, `${route.replaceAll("/", "-")}.png`),
        fullPage: true,
      });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
      ).toBe(true);
      outcomes.push(`Live authenticated ${route} render`);
    }
    for (const [name, route] of [
      ["customer-profile", "customers/" + fixtures.leadId],
      ["assistant-editor", "agents/" + fixtures.agentId + "?tab=config"],
      [
        "assistant-knowledge",
        "products/chat/assistants/" + fixtures.agentId + "/knowledge",
      ],
      ["assistant-playground", "chat?agent=" + fixtures.agentId],
    ]) {
      await page.waitForTimeout(12000);
      await page.goto(`${base}/app/${route}`);
      await expect(page.getByTestId("profile-menu")).toBeVisible({
        timeout: 30000,
      });
      await expect(page.locator('main [aria-busy="true"]')).toHaveCount(0, {
        timeout: 30000,
      });
      await expect(page.getByTestId("error-boundary-screen")).toHaveCount(0);
      if (name === "customer-profile") {
        await page
          .getByLabel("Customer notes")
          .fill("Notes verified in the migrated customer profile.");
        const saved = page.waitForResponse(
          (response) =>
            response.url().endsWith("/api/leads/" + fixtures.leadId) &&
            response.request().method() === "PATCH",
        );
        await page.getByRole("button", { name: "Save notes" }).click();
        expect((await saved).status()).toBe(200);
        await page.reload();
        await expect(page.getByLabel("Customer notes")).toHaveValue(
          "Notes verified in the migrated customer profile.",
          { timeout: 30000 },
        );
        outcomes.push("Migrated customer notes persisted across reload");
      }
      await page.screenshot({
        path: path.join(output, name + ".png"),
        fullPage: true,
      });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
      ).toBe(true);
      outcomes.push("Live migrated " + name + " render");
    }
    await page.getByTestId("profile-menu").getByRole("button").first().click();
    await page.getByRole("menuitem", { name: /sign out|log out/i }).click();
    await expect(page).toHaveURL(/\/login$/);
    await page.goto(`${base}/app/dashboard`);
    await expect(page).toHaveURL(/\/login/);
    outcomes.push("Logout and anonymous protected-route rejection");
    expect(errors).toEqual([]);
    console.log(`Real local browser checks passed: ${outcomes.length}`);
  } catch (error) {
    if (page)
      await page
        .locator("input")
        .evaluateAll((inputs) =>
          inputs.forEach((input) => {
            input.value = "";
          }),
        )
        .catch(() => {});
    if (page)
      await page
        .screenshot({ path: path.join(output, "failure.png"), fullPage: true })
        .catch(() => {});
    throw error;
  } finally {
    if (browser) await browser.close();
    execFileSync(
      python,
      [
        "-c",
        "import asyncio,sys; sys.path.insert(0,'scripts'); from verify_product_local import cleanup; asyncio.run(cleanup(sys.argv[1]))",
        email,
      ],
      { cwd: backend, stdio: "pipe" },
    );
    fs.writeFileSync(
      path.join(output, "verification.json"),
      JSON.stringify({ outcomes, errors, failedRequests }, null, 2),
    );
  }
})().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
