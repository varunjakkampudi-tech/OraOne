const { test, expect } = require("@playwright/test");

test("public marketing does not claim unverified certifications or customer proof", async ({ page }) => {
  for (const route of ["/security", "/documentation", "/ai-chat-agent"]) {
    await page.goto(route);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("body")).not.toContainText(/Big Four|Type I in audit|99\.9% uptime|Acme Health|Brightside Realty|GDPR-compliant/i);
  }
  await page.goto("/security");
  await expect(page.locator('a[href="https://github.com/varunjakkampudi-tech/OraOne/security/advisories/new"]')).toBeVisible();
});
