// Consent provenance for leads imported from a CSV file. The backend records the
// source and a plain-language note in the lead's extra blob; other sources show nothing.

export const IMPORT_CONSENT_SOURCE = "import_csv";

export type LeadExtra = Record<string, unknown> | null | undefined;

export type ImportConsentLine = { value: string; note: string };

// Returns the consent value and note to show beside a lead's consent, or null when
// the lead did not come from a CSV import or has no usable note.
export function importConsentLine(extra: LeadExtra): ImportConsentLine | null {
  if (!extra || extra["consent_source"] !== IMPORT_CONSENT_SOURCE) return null;
  const rawNote = extra["consent_note"];
  const note = typeof rawNote === "string" ? rawNote.trim() : "";
  if (!note) return null;
  const rawValue = extra["consent"];
  const value = typeof rawValue === "string" && rawValue.trim() ? rawValue.trim() : "unknown";
  return { value, note };
}
