import { describe, expect, it } from "vitest";
import {
  accessPolicy,
  demoAssistants,
  visibleConversationId,
  isWorkspaceDestinationActive,
  recoveryPath,
  sampleWorkspaceName,
} from "@/lib/oraone";
import { validateAuthFields } from "@/lib/phase2";

describe("Review requirements", () => {
  it("maps sales to Sales Assistant and its knowledge", () => {
    expect(demoAssistants.find((a) => a.id === "sales")?.name).toBe("Sales Assistant");
    expect(demoAssistants.find((a) => a.id === "sales")?.sources).toBe(28);
  });
  it("replaces hidden inbox selection", () => {
    expect(visibleConversationId("olivia", "Open", "")).toBe("lana");
  });
  it("clears selection without search matches", () => {
    expect(visibleConversationId("olivia", "Open", "no-such-person")).toBeUndefined();
  });
  it("selects only Inbox when Inbox is open", () => {
    expect(
      ["/app", "/app/inbox", "/app/analytics"].filter((to) =>
        isWorkspaceDestinationActive("/app/inbox", to),
      ),
    ).toEqual(["/app/inbox"]);
  });
  it("selects only Analytics for nested analytics pages", () => {
    expect(
      ["/app", "/app/inbox", "/app/analytics"].filter((to) =>
        isWorkspaceDestinationActive("/app/analytics/conversations", to),
      ),
    ).toEqual(["/app/analytics"]);
  });
  it("uses Acme Corporation consistently", () => {
    expect(sampleWorkspaceName).toBe("Acme Corporation");
  });
  it("keeps access free for everyone", () => {
    expect(accessPolicy.freeForEveryone).toBe(true);
  });
  it("disables payments", () => {
    expect(accessPolicy.paymentsEnabled).toBe(false);
  });
  it("has one canonical recovery destination", () => {
    expect(recoveryPath).toBe("/auth/sign-in");
  });
  it.each(["sign-in", "sign-up"])("does not require a password for email-code %s", (mode) => {
    expect(
      validateAuthFields(mode, {
        name: "Alex",
        email: "alex@example.com",
        password: "",
        confirm: "",
        code: "",
        terms: true,
      }),
    ).toEqual({});
  });
});
