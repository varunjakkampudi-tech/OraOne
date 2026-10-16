// Helpers shared by the sign-in screens. Kept out of components so Fast Refresh works.

export const RESEND_SECONDS = 60;

export function safeRedirect(value: unknown): string {
  return typeof value === "string" && value.startsWith("/") && !value.startsWith("//")
    ? value
    : "/studio";
}
