import { describe, expect, it } from "vitest";
import { RESEND_SECONDS, safeRedirect } from "@/lib/auth-redirect";

describe("passwordless sign-in rules", () => {
  it("returns to same-site pages only", () => {
    expect(safeRedirect("/studio/assistants/1")).toBe("/studio/assistants/1");
    expect(safeRedirect("//evil.com")).toBe("/studio");
    expect(safeRedirect("https://evil.com")).toBe("/studio");
    expect(safeRedirect(null)).toBe("/studio");
  });
  it("waits 60 seconds before resending a code", () => {
    expect(RESEND_SECONDS).toBe(60);
  });
});
