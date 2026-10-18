import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, messageOf } from "@/lib/api/client";
import {
  listAdminFeatureFlags,
  setCohortFlagMember,
  setOrganizationFlagOverride,
  type AdminFlag,
} from "@/lib/api/feature-flags";
import {
  OVERRIDE_CHOICES,
  cohortEmailProblem,
  organizationIdProblem,
  overrideValue,
  type OverrideChoice,
} from "@/lib/admin-beta";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; flags: AdminFlag[] }
  | { kind: "signin"; message: string }
  | { kind: "error"; message: string };

type Notice = { tone: "ok" | "error"; text: string };

function FlagCard({ flag, onSaved }: { flag: AdminFlag; onSaved: (notice: Notice) => void }) {
  const [orgId, setOrgId] = useState("");
  const [orgChoice, setOrgChoice] = useState<OverrideChoice>("enable");
  const [orgError, setOrgError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [cohortChoice, setCohortChoice] = useState<OverrideChoice>("enable");
  const [cohortError, setCohortError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submitOrganization = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const problem = organizationIdProblem(orgId);
    setOrgError(problem);
    if (problem) return;
    setBusy(true);
    try {
      const result = await setOrganizationFlagOverride(
        flag.key,
        orgId.trim(),
        overrideValue(orgChoice),
      );
      onSaved({
        tone: "ok",
        text: `${flag.key} for organisation ${orgId.trim()}: ${
          result.enabled === null ? "override removed" : result.enabled ? "on" : "off"
        }. Recorded in the audit log.`,
      });
      setOrgId("");
    } catch (error) {
      onSaved({ tone: "error", text: messageOf(error, "The change could not be saved.") });
    } finally {
      setBusy(false);
    }
  };

  const submitCohort = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const problem = cohortEmailProblem(email);
    setCohortError(problem);
    if (problem) return;
    setBusy(true);
    try {
      const result = await setCohortFlagMember(flag.key, email.trim(), overrideValue(cohortChoice));
      onSaved({
        tone: "ok",
        text: `${flag.key} for one beta tester: ${
          result.enabled === null ? "override removed" : result.enabled ? "on" : "off"
        }. Recorded in the audit log.`,
      });
      setEmail("");
    } catch (error) {
      onSaved({ tone: "error", text: messageOf(error, "The change could not be saved.") });
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="rounded-md border p-4" aria-labelledby={`flag-${flag.key}`}>
      <h3 id={`flag-${flag.key}`} className="break-all text-base font-semibold">
        {flag.key}
      </h3>
      <p className="mt-1 text-sm text-muted-foreground">{flag.description}</p>
      <p className="mt-2 text-xs text-muted-foreground">
        Off by default. Code rollout lists: {flag.code_rollout.organization_count} organisations,{" "}
        {flag.code_rollout.member_count} testers. Beta cohort: {flag.cohort.member_count} testers (
        {flag.cohort.enabled_count} on, {flag.cohort.disabled_count} off).
      </p>

      {flag.organization_overrides.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium">Organisation overrides</p>
          <ul className="mt-1 grid gap-1 text-xs">
            {flag.organization_overrides.map((override) => (
              <li key={override.organization_id} className="break-all">
                {override.organization_id}: {override.enabled ? "on" : "off"}
              </li>
            ))}
          </ul>
        </div>
      )}

      <form
        onSubmit={submitOrganization}
        className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end"
        noValidate
      >
        <div className="grid gap-1">
          <Label htmlFor={`org-${flag.key}`}>Organisation ID</Label>
          <Input
            id={`org-${flag.key}`}
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
            placeholder="00000000-0000-0000-0000-000000000000"
            aria-invalid={orgError ? true : undefined}
            aria-describedby={orgError ? `org-${flag.key}-error` : undefined}
          />
          {orgError && (
            <p id={`org-${flag.key}-error`} className="text-xs text-destructive">
              {orgError}
            </p>
          )}
        </div>
        <div className="grid gap-1">
          <Label htmlFor={`org-choice-${flag.key}`}>Change</Label>
          <select
            id={`org-choice-${flag.key}`}
            className="h-9 rounded-md border bg-background px-2 text-sm"
            value={orgChoice}
            onChange={(e) => setOrgChoice(e.target.value as OverrideChoice)}
          >
            {OVERRIDE_CHOICES.map((choice) => (
              <option key={choice.value} value={choice.value}>
                {choice.label}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit" disabled={busy}>
          Save organisation
        </Button>
      </form>

      <form
        onSubmit={submitCohort}
        className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end"
        noValidate
      >
        <div className="grid gap-1">
          <Label htmlFor={`email-${flag.key}`}>Beta tester email</Label>
          <Input
            id={`email-${flag.key}`}
            type="email"
            autoComplete="off"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={cohortError ? true : undefined}
            aria-describedby={cohortError ? `email-${flag.key}-error` : undefined}
          />
          {cohortError && (
            <p id={`email-${flag.key}-error`} className="text-xs text-destructive">
              {cohortError}
            </p>
          )}
        </div>
        <div className="grid gap-1">
          <Label htmlFor={`cohort-choice-${flag.key}`}>Change</Label>
          <select
            id={`cohort-choice-${flag.key}`}
            className="h-9 rounded-md border bg-background px-2 text-sm"
            value={cohortChoice}
            onChange={(e) => setCohortChoice(e.target.value as OverrideChoice)}
          >
            {OVERRIDE_CHOICES.map((choice) => (
              <option key={choice.value} value={choice.value}>
                {choice.label}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit" variant="outline" disabled={busy}>
          Save tester
        </Button>
      </form>
      <p className="mt-2 text-xs text-muted-foreground">
        Tester emails are stored only as a one-way hash. The audit log records the hash, not the
        address.
      </p>
    </article>
  );
}

export function AdminBetaPanel() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [notice, setNotice] = useState<Notice | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await listAdminFeatureFlags();
      setState({ kind: "ready", flags: data.flags });
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        setState({
          kind: "signin",
          message:
            error.status === 403
              ? "This account is not a super-admin. Only super-admins can change beta flags."
              : "Sign in with a super-admin account to manage beta flags.",
        });
      } else {
        setState({
          kind: "error",
          message: messageOf(error, "Beta flags could not be loaded. Try again shortly."),
        });
      }
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleSaved = (result: Notice) => {
    setNotice(result);
    if (result.tone === "ok") void load();
  };

  return (
    <section aria-labelledby="admin-beta-heading" className="admin-section">
      <h2 id="admin-beta-heading">Beta feature flags</h2>
      <p className="admin-table-summary">
        Flags are off unless turned on here, in the code rollout lists, or for a specific
        organisation or tester. Changes apply within about a minute and are recorded in the audit
        log.
      </p>

      {notice && (
        <div
          role="status"
          className={`mb-4 rounded-md border p-4 text-sm ${notice.tone === "error" ? "border-destructive text-destructive" : ""}`}
        >
          {notice.text}
        </div>
      )}

      {state.kind === "loading" && <p className="text-sm text-muted-foreground">Loading flags…</p>}

      {state.kind === "signin" && (
        <div className="admin-access-notice">
          <ShieldCheck />
          <div>
            <strong>Super-admin access required</strong>
            <p>{state.message}</p>
          </div>
        </div>
      )}

      {state.kind === "error" && (
        <p role="alert" className="text-sm text-destructive">
          {state.message}
        </p>
      )}

      {state.kind === "ready" && (
        <div className="grid gap-4">
          {state.flags.map((flag) => (
            <FlagCard key={flag.key} flag={flag} onSaved={handleSaved} />
          ))}
        </div>
      )}
    </section>
  );
}
