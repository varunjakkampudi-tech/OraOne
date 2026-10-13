const { test, expect } = require("@playwright/test");

test("assistant knowledge saves only the selected assistant and preserves explicit empty selection", async ({
  page,
}) => {
  const user = {
    id: "test-user",
    userId: "test-user",
    email: "test@example.com",
    role: "user",
    status: "active",
  };
  const agentId = "22222222-2222-4222-8222-222222222222";
  const kbId = "33333333-3333-4333-8333-333333333333";
  let ids = [kbId];
  const updates = [];
  await page.addInitScript(() => {
    localStorage.setItem("oraone_access_token", "test-token");
    localStorage.setItem("oraone_tour_seen_v1", "1");
  });
  await page.route(
    (url) => url.pathname.startsWith("/api/"),
    async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
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
      else if (path === `/api/agents/${agentId}`) {
        if (request.method() === "PUT") {
          const payload = request.postDataJSON();
          updates.push({ path, payload });
          ids = payload.knowledge_base_ids;
        }
        body = {
          id: agentId,
          name: "Selected assistant",
          knowledge_base_ids: ids,
        };
      } else if (path === "/api/knowledge-bases")
        body = {
          items: [{ id: kbId, name: "Selected knowledge", status: "active" }],
          total: 1,
        };
      await route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    },
  );
  await page.goto(`/app/products/chat/assistants/${agentId}/knowledge`);
  await expect(
    page.getByText("Selected assistant", { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("checkbox")).toBeChecked();
  await page.getByRole("checkbox").uncheck();
  await page.getByRole("button", { name: "Save binding" }).click();
  await expect(
    page.getByRole("button", { name: "Save binding" }),
  ).toBeDisabled();
  expect(updates).toEqual([
    { path: `/api/agents/${agentId}`, payload: { knowledge_base_ids: [] } },
  ]);
  await page.reload();
  await expect(page.getByRole("checkbox")).not.toBeChecked();
  await expect(
    page.getByText("0 explicitly selected", { exact: true }),
  ).toBeVisible();
});
