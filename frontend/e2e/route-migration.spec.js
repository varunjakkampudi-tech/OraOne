const { test, expect } = require("@playwright/test");
const referenceRoutes = require("./route-inventory.json");

const user = {
  userId: "local-user-1",
  id: "local-user-1",
  email: "user@example.test",
  name: "Local User",
  full_name: "Local User",
  role: "user",
  platform_role: "user",
  plan: "free",
  status: "active",
  created_at: "2026-01-01T00:00:00Z",
};

const adminUser = {
  ...user,
  role: "super_admin",
  platform_role: "super_admin",
};

const identityFor = (account) => ({
  user: account,
  organization: {
    id: "local-org-1",
    name: "Local Workspace",
    slug: "local-workspace",
    plan: "free",
  },
  membership: {
    organization_id: "local-org-1",
    role: "owner",
    status: "active",
  },
  is_new_user: false,
});

test("all reference destinations render or resolve to a designed page", async ({
  page,
}, testInfo) => {
  test.setTimeout(720_000);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(
    ({ regularIdentity, ownerIdentity }) => {
      localStorage.setItem("oraone_access_token", "test-admin-token");
      localStorage.setItem("oraone_identity", JSON.stringify(ownerIdentity));
      localStorage.setItem("oraone_tour_seen_v1", "1");
    },
    {
      ownerIdentity: identityFor(adminUser),
    },
  );

  await page.route(
    (url) => {
      const parsed = new URL(url);
      return (
        ["localhost", "127.0.0.1"].includes(parsed.hostname) &&
        parsed.port === "8000" &&
        parsed.pathname.startsWith("/api/")
      );
    },
    async (route) => {
      const request = route.request();
      const pathname = new URL(request.url()).pathname;
      const authorization = request.headers().authorization || "";
      const isOwner = authorization.includes("test-admin-token");
      const isAuthenticated =
        isOwner || authorization.includes("test-access-token");
      let status = 200;
      let body = {
        items: [],
        customers: [],
        products: [],
        events: [],
        models: [],
        fallback_models: [],
        disabled_models: [],
        default_model: "",
        retrieval: {},
        totals: {},
        summary: {},
      };

      if (pathname.endsWith("/auth/me")) {
        status = isAuthenticated ? 200 : 401;
        body = isOwner ? adminUser : user;
      } else if (pathname.endsWith("/auth/identity")) {
        status = isAuthenticated ? 200 : 401;
        body = identityFor(isOwner ? adminUser : user);
      } else if (pathname.endsWith("/super-admin/me")) {
        status = isOwner ? 200 : 403;
        body = { email: adminUser.email, role: "super_admin" };
      } else if (pathname.endsWith("/super-admin/audit-logs")) {
        body = [];
      } else if (pathname.endsWith("/super-admin/products")) {
        body = [];
      } else if (pathname.endsWith("/super-admin/feature-flags")) {
        body = [];
      } else if (pathname.endsWith("/super-admin/infrastructure")) {
        body = {
          summary: { total: 0, operational: 0, down: 0 },
          host: { cpu: null, ram: null },
          services: [],
          note: "Isolated browser-test fixture; not live infrastructure data.",
        };
      } else if (pathname.endsWith("/super-admin/usage")) {
        body = { totals: [], top_organizations: [] };
      } else if (/\/super-admin\/customers\/[^/]+$/.test(pathname)) {
        body = {
          name: "Test workspace",
          slug: "test-workspace",
          plan: "free",
          created_at: "2026-01-01T00:00:00Z",
          owner: null,
          counts: {
            agents: 0,
            conversations: 0,
            leads: 0,
            documents: 0,
            api_keys: 0,
            integrations: 0,
          },
          members: [],
          recent_conversations: [],
        };
      } else if (pathname.endsWith("/entitlements/me")) {
        body = { products: {}, features: {}, statuses: {}, catalog: [] };
      } else if (pathname.endsWith("/projects")) {
        body = { items: [] };
      } else if (pathname.endsWith("/agents")) {
        body = {
          items: [
            {
              id: "00000000-0000-4000-8000-000000000001",
              name: "Preview agent",
            },
          ],
        };
      } else if (pathname.endsWith("/channels")) {
        body = { items: [] };
      } else if (pathname.endsWith("/deploy")) {
        body = {
          agent_id: "00000000-0000-4000-8000-000000000001",
          agent_name: "Preview agent",
          public_key: "preview-public-key",
          widget_id: "00000000-0000-4000-8000-000000000002",
          widget_status: "draft",
          deploy_status: "draft",
          cdn_base: "https://cdn.example.test",
          api_base: "https://api.example.test",
          snippets: {
            one_line: "<!-- Browser test fixture -->",
            sdk: "// Browser test fixture",
            npm_install: "npm install @oraone/widget",
            npm_import: "import OraOne from '@oraone/widget';",
          },
          sdk_methods: [],
          install_guides: [],
          trigger_snippets: [],
          domains: [],
          verification: { installed: false, events_count: 0, loads_count: 0 },
          theme: {},
          settings: {},
        };
      } else if (pathname.endsWith("/leads/stats")) {
        body = {};
      } else if (
        pathname.endsWith("/leads") ||
        pathname.endsWith("/v2/conversations") ||
        pathname.endsWith("/messages") ||
        pathname.endsWith("/activity") ||
        pathname.endsWith("/notifications") ||
        pathname.endsWith("/team/members")
      ) {
        body = [];
      }

      await route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    },
  );

  const failures = [];
  const pageErrors = [];
  const consoleErrors = [];
  const moduleResponses = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("response", (response) => {
    if (
      response.url().includes("/src/pages/dashboard/Agents.jsx") ||
      (response.headers()["content-type"] || "").includes("application/json")
    ) {
      moduleResponses.push({
        status: response.status(),
        contentType: response.headers()["content-type"],
        url: response.url(),
      });
    }
  });
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  for (const route of referenceRoutes) {
    const destination = route.path.replace(
      /\$([A-Za-z][A-Za-z0-9_]*)/g,
      "codex-test-id",
    );
    try {
      if (route === referenceRoutes[0]) {
        await page.goto(destination, { waitUntil: "domcontentloaded" });
      } else {
        await page.evaluate((path) => {
          window.history.pushState({}, "", path);
          window.dispatchEvent(new PopStateEvent("popstate"));
        }, destination);
        await page.waitForTimeout(200);
        const lazyRouteLoader = page.getByTestId("oraone-loader");
        if (await lazyRouteLoader.isVisible().catch(() => false)) {
          await lazyRouteLoader.waitFor({ state: "detached", timeout: 8_000 });
        }
      }
      await page.locator("#root > *").first().waitFor({ timeout: 8_000 });
      await page.waitForTimeout(80);

      const errorBoundary = await page
        .getByTestId("error-boundary-screen")
        .count();
      const emptyRoot = await page
        .locator("#root")
        .evaluate((root) => !root.firstElementChild);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > window.innerWidth + 1,
      );
      if (errorBoundary || emptyRoot || overflow) {
        failures.push({
          path: route.path,
          type: route.type,
          resolvedPath: page.url(),
          errorBoundary: Boolean(errorBoundary),
          emptyRoot,
          horizontalOverflow: overflow,
        });
        if (errorBoundary || emptyRoot) break;
      }
    } catch (error) {
      failures.push({
        path: route.path,
        type: route.type,
        error: error.message,
      });
    }
  }

  await testInfo.attach("route-migration-failures.json", {
    body: JSON.stringify(
      {
        routeCount: referenceRoutes.length,
        failures,
        pageErrors,
        consoleErrors,
        moduleResponses,
      },
      null,
      2,
    ),
    contentType: "application/json",
  });
  expect(pageErrors, "browser runtime errors during route coverage").toEqual(
    [],
  );
  expect(
    failures,
    `unhealthy reference destinations: ${JSON.stringify({ failures, pageErrors, consoleErrors, moduleResponses })}`,
  ).toEqual([]);
  expect(referenceRoutes).toHaveLength(283);
});
