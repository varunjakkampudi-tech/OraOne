const { test, expect } = require("@playwright/test");

test("failed Product 1 sources are unavailable, not fabricated empty data", async ({
  page,
}) => {
  let fail = true;
  const user = {
    id: "test-user",
    userId: "test-user",
    email: "test@example.com",
    role: "user",
    status: "active",
  };
  await page.addInitScript(() => {
    localStorage.setItem("oraone_access_token", "test-token");
    localStorage.setItem("oraone_tour_seen_v1", "1");
  });
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const path = new URL(route.request().url()).pathname;
      let status = 200;
      let body = { items: [], total: 0 };
      if (path === "/api/auth/me") body = user;
      else if (path === "/api/auth/identity")
        body = {
          user,
          organization: {
            id: "test-org",
            name: "Test workspace",
            plan: "free",
          },
          membership: { role: "owner" },
          is_new_user: false,
        };
      else if (path === "/api/super-admin/me") status = 403;
      else if (
        path === "/api/agents" ||
        path === "/api/widgets" ||
        path === "/api/knowledge/stats"
      ) {
        if (fail) {
          status = 503;
          body = { detail: "Service unavailable" };
        } else if (path === "/api/knowledge/stats")
          body = { total_documents: 0 };
      }
      await route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    },
  );
  await page.goto("/app/products/chat");
  await expect(
    page.getByRole("heading", { name: "Chat workspace" }),
  ).toBeVisible();
  await expect(
    page.getByText("Unavailable", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByText("No agents yet", { exact: true })).toHaveCount(0);
  fail = false;
  await page
    .getByRole("button", { name: "Retry", exact: true })
    .first()
    .click();
  await expect(page.getByText("No agents yet", { exact: true })).toBeVisible();
  await expect(page.getByText("Unavailable", { exact: true })).toHaveCount(0);
});
