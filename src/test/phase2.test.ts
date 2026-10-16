import { describe, expect, it } from "vitest";
import { onboardingSteps, serviceCapabilities, validateAuthFields } from "@/lib/phase2";

describe("Phase 2 service boundaries", () => {
  it("does not simulate a connected identity service", () => {
    expect(serviceCapabilities.identityConnected).toBe(false);
  });
  it("does not grant platform administrator access", () => {
    expect(serviceCapabilities.adminAccessVerified).toBe(false);
  });
  it("does not imply contact messages are delivered", () => {
    expect(serviceCapabilities.contactDeliveryConnected).toBe(false);
  });
  it("does not imply model tests are available", () => {
    expect(serviceCapabilities.modelConnected).toBe(false);
  });
  it("preserves the nine specified onboarding steps", () => {
    expect(onboardingSteps.map((s) => s.path)).toEqual([
      "/onboarding",
      "/onboarding/profile",
      "/onboarding/workspace",
      "/onboarding/use-case",
      "/onboarding/ai-chat",
      "/onboarding/knowledge",
      "/onboarding/test",
      "/onboarding/install",
      "/onboarding/complete",
    ]);
  });
});

describe("Account form validation", () => {
  const valid = {
    name: "Alex",
    email: "alex@example.com",
    password: "example-password",
    confirm: "example-password",
    code: "123456",
    terms: true,
  };
  it("rejects an invalid email", () => {
    expect(validateAuthFields("sign-in", { ...valid, email: "invalid" })["email"]).toBeTruthy();
  });
  it("requires terms acknowledgment for sign up", () => {
    expect(validateAuthFields("sign-up", { ...valid, terms: false })["terms"]).toBeTruthy();
  });
  it("requires matching reset passwords", () => {
    expect(
      validateAuthFields("reset-password", { ...valid, confirm: "different" })["confirm"],
    ).toBeTruthy();
  });
  it("requires a six-digit verification code", () => {
    expect(validateAuthFields("mfa", { ...valid, code: "12" })["code"]).toBeTruthy();
  });
  it("accepts valid form input without implying authentication", () => {
    expect(validateAuthFields("sign-up", valid)).toEqual({});
  });
});
