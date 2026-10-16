export const onboardingSteps = [
  { title: "Welcome", path: "/onboarding" },
  { title: "Profile", path: "/onboarding/profile" },
  { title: "Workspace", path: "/onboarding/workspace" },
  { title: "Use case", path: "/onboarding/use-case" },
  { title: "AI Chat", path: "/onboarding/ai-chat" },
  { title: "Knowledge", path: "/onboarding/knowledge" },
  { title: "Test", path: "/onboarding/test" },
  { title: "Install", path: "/onboarding/install" },
  { title: "Complete", path: "/onboarding/complete" },
] as const;

// Preview capabilities are explicit, never inferred from a portfolio release label.
export const serviceCapabilities = {
  identityConnected: false,
  adminAccessVerified: false,
  contactDeliveryConnected: false,
  modelConnected: false,
  persistenceConnected: false,
  deploymentConnected: false,
} as const;

export function validateAuthFields(
  mode: string,
  fields: {
    name: string;
    email: string;
    password: string;
    confirm: string;
    terms: boolean;
    code: string;
  },
) {
  const errors: Record<string, string> = {};
  if (mode === "sign-up" && !fields.name.trim()) errors["name"] = "Enter your full name.";
  if (
    ["sign-in", "sign-up", "forgot-password"].includes(mode) &&
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fields.email)
  )
    errors["email"] = "Enter a valid email address.";
  if (mode === "reset-password" && !fields.password) errors["password"] = "Enter your password.";
  // Sign-in is passwordless (emailed code), so no password policy is validated here.
  if (mode === "reset-password" && fields.password !== fields.confirm)
    errors["confirm"] = "Passwords must match.";
  if (mode === "sign-up" && !fields.terms) errors["terms"] = "Acknowledge the terms to continue.";
  if (["mfa", "verify-email"].includes(mode) && !/^\d{6}$/.test(fields.code))
    errors["code"] = "Enter the six-digit code.";
  return errors;
}
