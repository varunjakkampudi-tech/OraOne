const { test, expect } = require("@playwright/test");

test("throttled session validation preserves credentials and requires a verified retry", async ({
  page,
}) => {
  let allowSession = false;
  const user = {
    id: "test-user",
    userId: "test-user",
    email: "test@example.com",
    role: "user",
    status: "active",
  };
  await page.addInitScript(() => {
    localStorage.setItem("oraone_access_token", "test-access-token");
    localStorage.setItem("oraone_tour_seen_v1", "1");
  });
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const pathname = new URL(route.request().url()).pathname;
      let status = 200;
      let body = { items: [] };
      if (pathname === "/api/auth/me") {
        status = allowSession ? 200 : 429;
        body = allowSession ? user : { detail: "Too many requests" };
      } else if (pathname === "/api/auth/identity") {
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
      } else if (pathname === "/api/super-admin/me") {
        status = 403;
      } else if (
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
  await page.goto("/app/dashboard");
  await expect(page.getByTestId("session-verification-error")).toBeVisible();
  await expect(page.getByTestId("profile-menu")).toHaveCount(0);
  expect(
    await page.evaluate(() => localStorage.getItem("oraone_access_token")),
  ).toBe("test-access-token");
  allowSession = true;
  await page.getByTestId("session-verification-retry").click();
  await expect(page.getByTestId("profile-menu")).toBeVisible();
  await expect(page.getByTestId("session-verification-error")).toHaveCount(0);
});
