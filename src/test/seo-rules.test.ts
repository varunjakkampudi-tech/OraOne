import { describe, expect, it } from "vitest";
import { isIndexablePath, pageHead } from "@/lib/oraone";

describe("OraOne indexing boundaries", () => {
  it.each([
    "/app",
    "/app/customers",
    "/admin",
    "/admin/users",
    "/auth/sign-in",
    "/onboarding",
    "/reset-password",
  ])("excludes private preview %s", (path) => {
    expect(isIndexablePath(path)).toBe(false);
  });
  it.each(["/privacy", "/terms", "/cookies", "/acceptable-use", "/refund-policy"])(
    "excludes unapproved policy %s",
    (path) => {
      expect(isIndexablePath(path)).toBe(false);
    },
  );
  it.each(["/", "/platform", "/products/ai-chat", "/contact"])(
    "allows public destination %s",
    (path) => {
      expect(isIndexablePath(path)).toBe(true);
    },
  );
  it("canonical references the leaf page rather than the homepage", () => {
    expect(pageHead("Contact", "/contact").links).toEqual([
      { rel: "canonical", href: "https://oraone.in/contact" },
    ]);
  });
});
