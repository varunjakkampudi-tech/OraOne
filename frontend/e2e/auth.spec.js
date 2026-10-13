const { test, expect } = require("@playwright/test");

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
  createdAt: "2026-01-01T00:00:00Z",
};

const identity = {
  user: { ...user, created_at: user.createdAt },
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
};

async function mockUnauthenticatedApi(page) {
  // UI integration tests are isolated from real services. Specific test routes
  // registered later override these contract-shaped empty service responses.
  await page.route("**/api/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    const body = path.endsWith("/health")
      ? { status: "ok" }
      : path.endsWith("/team/members") || path.endsWith("/team/invitations")
        ? []
        : { items: [], total: 0, notifications: [], unread_count: 0 };
    return route.fulfill({
      status: path.endsWith("/super-admin/me") ? 403 : 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({ status: 401, contentType: "application/json", body: "{}" }),
  );
  await page.route("**/api/auth/identity", (route) =>
    route.fulfill({ status: 401, contentType: "application/json", body: "{}" }),
  );
}

test.describe("self-hosted email authentication", () => {
  test.beforeEach(async ({ page }) => mockUnauthenticatedApi(page));

  test("signup submits to the application and presents email verification", async ({
    page,
  }) => {
    let signupPayload;
    await page.route("**/api/auth/signup", async (route) => {
      signupPayload = route.request().postDataJSON();
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ message: "Signup successful." }),
      });
    });

    await page.goto("/signup");
    await page.getByTestId("signup-name-input").fill("Local User");
    await page.getByTestId("signup-email-input").fill("user@example.test");
    await page.getByTestId("signup-password-input").fill("OraOne-Test!2026");
    await page.getByTestId("signup-confirm-input").fill("OraOne-Test!2026");
    await page.getByTestId("signup-terms").check({ force: true });
    await page.getByTestId("signup-submit").click();

    await expect(page).toHaveURL(/\/verify-email$/);
    await expect(page.getByTestId("verify-email-form")).toBeVisible();
    await expect(page.getByText("user@example.test")).toBeVisible();
    expect(signupPayload).toEqual({
      email: "user@example.test",
      password: "OraOne-Test!2026",
      name: "Local User",
    });
  });

  test("email verification handles code submission and resend", async ({
    page,
  }) => {
    await page.clock.install();
    const requests = [];
    await page.route("**/api/auth/verify", (route) => {
      requests.push(["verify", route.request().postDataJSON()]);
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "{}",
      });
    });
    await page.route("**/api/auth/resend", (route) => {
      requests.push(["resend", route.request().postDataJSON()]);
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "{}",
      });
    });
    await page.goto("/verify-email");
    await page.getByTestId("verify-email-input").fill("user@example.test");
    await page.clock.runFor(46_000);
    await page.getByTestId("verify-resend").click();
    for (const [index, digit] of [..."123456"].entries()) {
      await page
        .getByTestId("verify-code-input")
        .getByLabel(`Digit ${index + 1}`)
        .fill(digit);
    }
    await page.getByTestId("verify-submit").click();
    await expect(page).toHaveURL(/\/login$/);
    expect(requests).toEqual([
      ["resend", { email: "user@example.test" }],
      ["verify", { email: "user@example.test", code: "123456" }],
    ]);
  });

  test("password login requires OTP, then establishes a protected session", async ({
    page,
  }) => {
    const requests = [];
    await page.route("**/api/auth/login", (route) => {
      requests.push(["login", route.request().postDataJSON()]);
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ otp_required: true }),
      });
    });
    await page.route("**/api/auth/login/verify-otp", (route) => {
      requests.push(["otp", route.request().postDataJSON()]);
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: "test-access",
          refresh_token: "test-refresh",
        }),
      });
    });
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(user),
      }),
    );
    await page.route("**/api/auth/identity", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(identity),
      }),
    );
    await page.route("**/api/analytics/overview", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({}),
      }),
    );
    await page.goto("/login");
    await page.getByTestId("login-email-input").fill("user@example.test");
    await page.getByTestId("login-password-input").fill("OraOne-Test!2026");
    await page.getByTestId("login-submit").click();
    await expect(page.getByTestId("login-otp-form")).toBeVisible();
    for (const [index, digit] of [..."654321"].entries()) {
      await page
        .getByTestId("login-otp-input")
        .getByLabel(`Digit ${index + 1}`)
        .fill(digit);
    }
    await page.getByTestId("login-otp-submit").click();
    await expect(page).toHaveURL(/\/app\/dashboard$/);
    expect(requests).toEqual([
      ["login", { email: "user@example.test", password: "OraOne-Test!2026" }],
      ["otp", { email: "user@example.test", code: "654321" }],
    ]);
  });

  test("password recovery sends a code and renders the reset form", async ({
    page,
  }) => {
    let forgotPayload;
    await page.route("**/api/auth/forgot-password", (route) => {
      forgotPayload = route.request().postDataJSON();
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "{}",
      });
    });
    await page.goto("/forgot-password");
    await page.getByTestId("forgot-email-input").fill("user@example.test");
    await page.getByTestId("forgot-submit-btn").click();
    await expect(page).toHaveURL(/\/reset-password$/);
    await expect(page.getByTestId("reset-password-form")).toBeVisible();
    await expect(page.getByTestId("reset-code-input")).toBeVisible();
    expect(forgotPayload).toEqual({ email: "user@example.test" });
  });

  test("protected routes reject anonymous users and logout clears an established session", async ({
    page,
  }) => {
    await page.goto("/app/dashboard");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByTestId("login-form")).toBeVisible();

    await page.route("**/api/auth/login", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: "test-access",
          refresh_token: "test-refresh",
        }),
      }),
    );
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(user),
      }),
    );
    await page.route("**/api/auth/identity", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(identity),
      }),
    );
    let logoutRequested = false;
    await page.route("**/api/auth/logout", (route) => {
      logoutRequested = true;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "{}",
      });
    });
    await page.goto("/login");
    await page.getByTestId("login-email-input").fill("user@example.test");
    await page.getByTestId("login-password-input").fill("OraOne-Test!2026");
    await page.getByTestId("login-submit").click();
    await expect(page).toHaveURL(/\/app\/dashboard$/);
    await page.getByRole("button", { name: "Open profile menu" }).click();
    await page.getByTestId("profile-logout").click();
    await expect(page).toHaveURL(/\/login$/);
    expect(logoutRequested).toBe(true);
    expect(
      await page.evaluate(() => localStorage.getItem("oraone_access_token")),
    ).toBeNull();
  });

  test("unified product portfolio presents all products with honest availability", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      localStorage.setItem("oraone_access_token", "test-access");
    });
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(user),
      }),
    );
    await page.route("**/api/auth/identity", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(identity),
      }),
    );
    await page.route("**/api/projects", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      }),
    );
    await page.goto("/app/products");
    await expect(page.getByTestId("product-portfolio-page")).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "One workspace. A growing product ecosystem.",
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "OraOne AI Chat Platform" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "OraOne OS" }),
    ).toBeVisible();
    expect(
      await page
        .getByTestId("product-portfolio-page")
        .getByText("Planned", { exact: true })
        .count(),
    ).toBe(8);
    await expect(
      page.getByText("Long-term vision", { exact: true }),
    ).toBeVisible();
  });

  test("agent setup routes app connections to the real integrations screen", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      localStorage.setItem("oraone_access_token", "test-access");
      // Keep the first-visit tour from covering controls on this deep-linked
      // wizard flow.
      localStorage.setItem("oraone_tour_seen_v1", "1");
    });
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(user),
      }),
    );
    await page.route("**/api/auth/identity", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(identity),
      }),
    );
    await page.route("**/api/projects", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      }),
    );
    await page.route("**/api/integrations", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          total: 2,
          items: [
            {
              catalog: {
                provider: "google_drive",
                name: "Google Drive",
                category: "documents",
                type: "storage",
                auth: "oauth",
                icon: "Cloud",
                color: "#1A73E8",
                description: "Sync Drive folders into the Knowledge Base.",
                available: true,
              },
              integration: null,
            },
            {
              catalog: {
                provider: "slack",
                name: "Slack",
                category: "communication",
                type: "other",
                auth: "oauth",
                icon: "MessageSquare",
                color: "#4A154B",
                description: "Search channels and messages.",
                available: false,
              },
              integration: null,
            },
          ],
        }),
      }),
    );
    let knowledgeBaseCreated = false;
    let fakeConnectRequested = false;
    await page.route("**/api/knowledge-bases", (route) => {
      knowledgeBaseCreated = true;
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ id: "unexpected-kb" }),
      });
    });
    await page.route("**/api/integrations/connect", (route) => {
      fakeConnectRequested = true;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ integration: { connection_type: "mock" } }),
      });
    });

    await page.goto("/app/create-agent");
    await page.getByRole("button", { name: /Website Chatbot/ }).click();
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("button", { name: "Connect an App" }).click();
    await page.getByRole("button", { name: /^G Google Drive$/ }).click();
    await page.getByRole("button", { name: "Continue" }).click();

    await expect(page).toHaveURL(/\/app\/integrations$/);
    await expect(
      page.getByRole("heading", { name: "Google Drive" }),
    ).toBeVisible();
    await expect(page.getByTestId("int-connect-cta")).toBeEnabled();
    await page.getByTestId("int-detail-close").click();
    await page.getByTestId("int-card-slack").click();
    await expect(
      page.getByTestId("int-card-slack").getByText("COMING SOON"),
    ).toBeVisible();
    await expect(page.getByTestId("int-connect-cta")).toBeDisabled();
    expect(knowledgeBaseCreated).toBe(false);
    expect(fakeConnectRequested).toBe(false);
  });

  test("Product 1 workspace shell adapts to mobile and keeps workspace switching reachable", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addInitScript(() => {
      localStorage.setItem("oraone_access_token", "test-access");
      localStorage.setItem("oraone_tour_seen_v1", "1");
    });
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(user),
      }),
    );
    await page.route("**/api/auth/identity", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(identity),
      }),
    );
    await page.route("**/api/projects", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      }),
    );
    await page.route("**/api/agents**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      }),
    );
    await page.route("**/api/knowledge-bases**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      }),
    );
    await page.route("**/api/team/members**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      }),
    );
    await page.route("**/api/analytics/overview**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ totals: {}, series: {} }),
      }),
    );
    await page.route("**/api/notifications**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ notifications: [], unread_count: 0 }),
      }),
    );

    await page.goto("/app/dashboard");
    const firstSetupTitle = page.getByText("Create first AI assistant");
    await expect(firstSetupTitle).toBeVisible();
    const titleBounds = await firstSetupTitle.boundingBox();
    expect(titleBounds.width).toBeGreaterThan(150);
    await expect(
      page.locator("header").getByTestId("dashboard-brand-home"),
    ).toBeVisible();
    await expect(page.getByTestId("dashboard-menu-btn")).toBeVisible();
    await page.getByTestId("dashboard-menu-btn").click();
    await expect(page.getByTestId("mobile-sidebar")).toBeVisible();
    await expect(
      page.getByTestId("mobile-sidebar").getByText("Local Workspace"),
    ).toBeVisible();
    await expect(
      page.getByTestId("mobile-sidebar").getByTestId("project-switcher-empty"),
    ).toBeVisible();
    await expect(
      page.getByTestId("mobile-sidebar").getByTestId("nav-product-portfolio"),
    ).toBeVisible();
    for (const destination of [
      "sidebar-analytics",
      "nav-widgets",
      "nav-team",
      "nav-usage",
      "nav-settings",
    ]) {
      await expect(
        page.getByTestId("mobile-sidebar").getByTestId(destination),
      ).toBeVisible();
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.keyboard.press("Escape");
    await expect(page.getByTestId("mobile-sidebar")).toHaveCount(0);
    await page.goto("/app/settings");
    await expect(
      page.getByRole("heading", { name: "Settings", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  });

  test("dashboard does not present an empty workspace when data requests fail", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      localStorage.setItem("oraone_access_token", "test-access");
      localStorage.setItem("oraone_tour_seen_v1", "1");
    });
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(user),
      }),
    );
    await page.route("**/api/auth/identity", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(identity),
      }),
    );
    await page.route("**/api/projects", (route) =>
      route.fulfill({ status: 503, body: "{}" }),
    );
    await page.route("**/api/agents**", (route) =>
      route.fulfill({ status: 503, body: "{}" }),
    );
    await page.route("**/api/analytics/overview**", (route) =>
      route.fulfill({ status: 503, body: "{}" }),
    );

    await page.goto("/app/dashboard");
    await expect(page.getByTestId("dashboard-data-unavailable")).toBeVisible();
    await expect(
      page
        .getByRole("button", { name: "Projects unavailable · Retry" })
        .first(),
    ).toBeVisible();
    await expect(page.getByText("Create first AI assistant")).toHaveCount(0);
  });

  test("imported Product 1 design URLs resolve to the functional application routes", async ({
    page,
  }) => {
    test.setTimeout(90_000);
    await page.addInitScript(() => {
      localStorage.setItem("oraone_access_token", "test-access");
      localStorage.setItem("oraone_tour_seen_v1", "1");
    });
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(user),
      }),
    );
    await page.route("**/api/auth/identity", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(identity),
      }),
    );
    await page.route("**/api/**", (route) => {
      const pathname = new URL(route.request().url()).pathname;
      if (!pathname.startsWith("/api/")) {
        return route.continue();
      }
      const body = pathname.endsWith("/auth/me")
        ? user
        : pathname.endsWith("/auth/identity")
          ? identity
          : pathname.endsWith("/v2/conversations") ||
              pathname.endsWith("/messages")
            ? []
            : { items: [], totals: {}, series: {} };
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    });

    const aliases = [
      ["/app/inbox", /\/app\/conversations$/],
      ["/app/inbox/conversation-1", /\/app\/conversations\/conversation-1$/],
      ["/app/customers/customer-1", /\/app\/customers\/customer-1$/],
      ["/app/leads/lead-1", /\/app\/leads\?lead=lead-1$/],
      ["/app/products/chat/assistants", /\/app\/agents$/],
      [
        "/app/products/chat/knowledge/websites",
        /\/app\/knowledge-base\/websites$/,
      ],
      [
        "/app/products/chat/assistants/agent-1/widget",
        /\/app\/agents\/agent-1\/deploy$/,
      ],
      [
        "/app/products/chat/assistants/agent-1/analytics",
        /\/app\/products\/chat\/assistants\/agent-1\/analytics$/,
      ],
      ["/app/integrations/webhooks", /\/app\/webhooks$/],
      [
        "/app/integrations/integration-1",
        /\/app\/integrations\?integration=integration-1$/,
      ],
      ["/app/settings/api-keys", /\/app\/api-keys$/],
      ["/app/settings/members", /\/app\/team$/],
      ["/app/billing/usage", /\/app\/usage$/],
      ["/app/products/chat/settings", /\/app\/settings$/],
    ];

    for (const [source, destination] of aliases) {
      await page.goto(source, { waitUntil: "domcontentloaded" });
      await expect(page.getByTestId("profile-menu")).toBeVisible({
        timeout: 15_000,
      });
      await expect(page).toHaveURL(destination);
    }
  });

  test("design-system authentication URLs preserve the local email flows", async ({
    page,
  }) => {
    const aliases = [
      ["/auth/sign-in", /\/login$/],
      ["/auth/sign-up", /\/signup$/],
      ["/auth/verify-email", /\/verify-email$/],
      ["/auth/forgot-password", /\/forgot-password$/],
      ["/auth/reset-password", /\/reset-password$/],
      ["/auth/session-expired", /\/login\?reason=session-expired$/],
    ];

    for (const [source, destination] of aliases) {
      await page.goto(source);
      await expect(page).toHaveURL(destination);
    }
  });

  test("primary Product 1 screens render inside the integrated shell without runtime errors", async ({
    page,
  }) => {
    test.setTimeout(120_000);
    const pageErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") pageErrors.push(message.text());
    });
    await page.addInitScript(() => {
      localStorage.setItem("oraone_access_token", "test-access");
      localStorage.setItem("oraone_tour_seen_v1", "1");
    });
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(user),
      }),
    );
    await page.route("**/api/auth/identity", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(identity),
      }),
    );
    await page.route("**/api/**", (route) => {
      if (!new URL(route.request().url()).pathname.startsWith("/api/")) {
        return route.continue();
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [],
          agents: [],
          projects: [],
          members: [],
          conversations: [],
          notifications: [],
          totals: {},
          series: {},
        }),
      });
    });

    const routes = [
      "/app/dashboard",
      "/app/agents",
      "/app/conversations",
      "/app/leads",
      "/app/analytics",
      "/app/knowledge-base",
      "/app/integrations",
      "/app/widgets",
      "/app/team",
      "/app/usage",
      "/app/settings",
      "/app/products",
    ];

    for (const route of routes) {
      await test.step(route, async () => {
        await page.goto(route);
        await expect(page).toHaveURL(
          new RegExp(`${route.replaceAll("/", "\\/")}$`),
        );
        await Promise.race([
          page.getByTestId("dashboard-brand-home").first().waitFor(),
          page.getByTestId("error-boundary-screen").waitFor(),
        ]);
        await expect(
          page.getByTestId("error-boundary-screen"),
          `${route} reached the application error boundary: ${pageErrors.join(" | ")}`,
        ).toHaveCount(0);
        expect(pageErrors, `${route} raised a browser exception`).toEqual([]);
        await expect(
          page.getByTestId("dashboard-brand-home").first(),
        ).toBeVisible();
        const hasHorizontalOverflow = await page.evaluate(
          () => document.documentElement.scrollWidth > window.innerWidth + 1,
        );
        expect(hasHorizontalOverflow, `${route} overflows horizontally`).toBe(
          false,
        );
      });
    }

    expect(pageErrors).toEqual([]);
  });

  test("design deep links open the matching lead and conversation records", async ({
    page,
  }) => {
    test.setTimeout(60_000);
    await page.addInitScript((storedIdentity) => {
      localStorage.setItem("oraone_access_token", "test-access");
      localStorage.setItem("oraone_identity", JSON.stringify(storedIdentity));
      localStorage.setItem("oraone_tour_seen_v1", "1");
    }, identity);

    const lead = {
      id: "lead-42",
      name: "Ada Lovelace",
      email: "ada@example.test",
      phone: "555-0100",
      status: "New",
      score: 82,
      temperature: "warm",
      created_at: "2026-10-01T10:00:00Z",
    };
    const conversation = {
      id: "conversation-42",
      channel: "chat",
      status: "active",
      customer_name: "Grace Hopper",
      customer_email: "grace@example.test",
      started_at: "2026-10-01T10:00:00Z",
      message_count: 1,
    };

    await page.route("**/api/**", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      let body = {};
      if (pathname.endsWith("/auth/me")) body = user;
      else if (pathname.endsWith("/auth/identity")) body = identity;
      else if (pathname.endsWith("/projects")) body = { items: [] };
      else if (pathname.endsWith("/leads/stats")) body = {};
      else if (pathname.endsWith("/leads")) body = [lead];
      else if (pathname.endsWith(`/leads/${lead.id}`)) body = lead;
      else if (pathname.endsWith(`/leads/${lead.id}/conversation`))
        body = { messages: [] };
      else if (pathname.endsWith("/v2/conversations")) body = [conversation];
      else if (
        pathname.endsWith(`/v2/conversations/${conversation.id}/messages`)
      )
        body = [];
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    });

    await page.goto(`/app/customers/${lead.id}`);
    await expect(page).toHaveURL(new RegExp(`/app/customers/${lead.id}$`));
    await expect(
      page.getByRole("heading", {
        name: lead.name,
      }),
    ).toBeVisible();

    await page.goto(`/app/inbox/${conversation.id}`);
    await expect(page).toHaveURL(
      new RegExp(`/app/conversations/${conversation.id}$`),
    );
    await expect(
      page.getByRole("heading", { name: conversation.customer_name }).first(),
    ).toBeVisible();
  });

  test("planned product designs are reachable without presenting fake live data", async ({
    page,
  }) => {
    await page.addInitScript((storedIdentity) => {
      localStorage.setItem("oraone_access_token", "test-access");
      localStorage.setItem("oraone_identity", JSON.stringify(storedIdentity));
      localStorage.setItem("oraone_tour_seen_v1", "1");
    }, identity);
    await page.route("**/api/**", async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      const body = pathname.endsWith("/auth/me")
        ? user
        : pathname.endsWith("/auth/identity")
          ? identity
          : pathname.endsWith("/projects")
            ? { items: [] }
            : pathname.endsWith("/entitlements/me")
              ? { products: {}, features: {}, statuses: {}, catalog: [] }
              : {};
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    });

    await page.goto("/app/products/voice/calls");
    await expect(page.getByTestId("planned-product-page")).toBeVisible();
    await expect(
      page.getByText("AI Voice", { exact: true }).last(),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Calls", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Design preview — not an active service"),
    ).toBeVisible();
    await expect(
      page.getByText(/There is no connected service, live workspace data/),
    ).toBeVisible();
    await expect(page.getByText(/sample|12,486|78\.4%/i)).toHaveCount(0);

    const productRoutes = [
      ["/app/products/voice/numbers", "Phone numbers"],
      ["/app/products/whatsapp/templates", "Templates"],
      ["/app/products/omnichannel/team-inbox", "Team inbox"],
      ["/app/products/automation/workflows/new", "Create a workflow"],
      ["/app/products/ai-studio/evaluations", "Evaluations"],
      ["/app/products/marketplace/explore", "Explore"],
      ["/app/products/mobile/availability", "Availability"],
      ["/app/products/enterprise/sso", "Single sign-on"],
      ["/app/products/oraone-os/command-center", "Command center"],
    ];
    for (const [path, screenTitle] of productRoutes) {
      await page.goto(path);
      await expect(page.getByTestId("planned-product-page")).toBeVisible();
      await expect(
        page.getByRole("heading", { name: screenTitle, exact: true }),
      ).toBeVisible();
    }

    await page.setViewportSize({ width: 390, height: 844 });
    const documentWidth = await page.evaluate(
      () => document.documentElement.scrollWidth,
    );
    expect(documentWidth).toBe(390);
  });

  test("planned product landing pages distinguish roadmap from availability", async ({
    page,
  }) => {
    const routes = [
      ["/products/ai-voice", "OraOne AI Voice Platform"],
      ["/products/whatsapp", "OraOne WhatsApp Platform"],
      ["/products/omnichannel", "Omnichannel Communication Hub"],
      ["/products/automation", "Workflow Automation Platform"],
      ["/products/ai-studio", "AI Studio & Agent Builder"],
      ["/products/marketplace", "Marketplace"],
      ["/products/mobile", "Mobile Applications"],
      ["/products/enterprise", "Enterprise Edition"],
      ["/products/oraone-os", "OraOne OS"],
    ];
    for (const [path, productName] of routes) {
      await page.goto(path);
      await expect(page.getByTestId("marketing-product-page")).toBeVisible();
      await expect(
        page.getByRole("heading", { name: productName, exact: true }),
      ).toBeVisible();
      await expect(
        page.getByText(/no release date or signup service has been announced/i),
      ).toBeVisible();
    }

    await page.goto("/products/ai-chat");
    await expect(page.getByTestId("marketing-product-page")).toBeVisible();
    await expect(
      page.getByRole("link", { name: /create an account/i }),
    ).toBeVisible();
  });

  test("owner console keeps its server-gated shell and compatibility routes", async ({
    page,
  }) => {
    test.setTimeout(90_000);
    const pageErrors = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("console", (message) => {
      if (message.type() === "error") pageErrors.push(message.text());
    });
    await page.addInitScript(() => {
      localStorage.setItem("oraone_access_token", "test-access");
      localStorage.setItem("oraone_tour_seen_v1", "1");
    });

    const adminUser = {
      ...user,
      role: "super_admin",
      platform_role: "super_admin",
    };
    const adminIdentity = { ...identity, user: adminUser };
    await page.route("**/api/auth/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(adminUser),
      }),
    );
    await page.route("**/api/auth/identity", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(adminIdentity),
      }),
    );
    await page.route("**/api/super-admin/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ email: adminUser.email, role: "super_admin" }),
      }),
    );
    await page.route("**/api/**", (route) => {
      if (!new URL(route.request().url()).pathname.startsWith("/api/")) {
        return route.continue();
      }
      const pathname = new URL(route.request().url()).pathname;
      if (
        pathname.endsWith("/auth/me") ||
        pathname.endsWith("/auth/identity") ||
        pathname.endsWith("/super-admin/me") ||
        pathname.endsWith("/super-admin/usage")
      ) {
        const body = pathname.endsWith("/auth/me")
          ? adminUser
          : pathname.endsWith("/auth/identity")
            ? adminIdentity
            : pathname.endsWith("/super-admin/me")
              ? { email: adminUser.email, role: "super_admin" }
              : { totals: [], top_organizations: [] };
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(body),
        });
      }
      if (pathname.endsWith("/super-admin/audit-logs")) {
        return route.fulfill({
          status: 200,
          contentType: "application/json",
          body: "[]",
        });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [],
          customers: [],
          products: [],
          events: [],
          totals: {},
          summary: {},
        }),
      });
    });

    const aliases = [
      ["/admin/audit", /\/admin\/audit-logs$/],
      ["/admin/ai-models", /\/admin\/ai-operations$/],
      ["/admin/organizations", /\/admin\/workspaces$/],
      ["/admin/organizations/org-1", /\/admin\/customers\?customer=org-1$/],
      ["/admin/users", /\/admin\/users$/],
      ["/admin/users/user-1", /\/admin\/users\/user-1$/],
      ["/owner/usage", /\/admin\/usage$/],
      ["/owner/organizations/org-1", /\/admin\/customers\?customer=org-1$/],
    ];
    for (const [source, destination] of aliases) {
      await page.goto(source);
      await expect(page).toHaveURL(destination);
    }

    await page.goto("/admin");
    await Promise.race([
      page
        .getByRole("button", { name: /Search customers, pages, agents/i })
        .waitFor(),
      page.getByTestId("error-boundary-screen").waitFor(),
    ]);
    await expect(
      page.getByTestId("error-boundary-screen"),
      `Owner console reached the application error boundary: ${pageErrors.join(" | ")}`,
    ).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: /Search customers, pages, agents/i }),
    ).toBeVisible();
    await expect(page.getByText("Restricted area")).toHaveCount(0);
    await expect(page.getByTestId("error-boundary-screen")).toHaveCount(0);
    expect(pageErrors).toEqual([]);
  });
});
