// Validation and mapping for the beta flag console. The server re-checks every value.

export type OverrideChoice = "enable" | "disable" | "remove";

export const OVERRIDE_CHOICES: { value: OverrideChoice; label: string }[] = [
  { value: "enable", label: "Turn on" },
  { value: "disable", label: "Turn off" },
  { value: "remove", label: "Remove override" },
];

/** Maps a choice to the API value: true, false, or null to remove the override. */
export function overrideValue(choice: OverrideChoice): boolean | null {
  if (choice === "enable") return true;
  if (choice === "disable") return false;
  return null;
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function organizationIdProblem(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return "Enter the organisation ID.";
  if (!UUID_PATTERN.test(trimmed)) return "The organisation ID must be a UUID.";
  return null;
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function cohortEmailProblem(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return "Enter the tester's email address.";
  if (trimmed.length > 320 || !EMAIL_PATTERN.test(trimmed)) return "Enter a valid email address.";
  return null;
}
