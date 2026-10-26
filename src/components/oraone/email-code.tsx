import { useEffect, useState } from "react";
import { RESEND_SECONDS, safeRedirect } from "@/lib/auth-redirect";
import { useNavigate } from "@tanstack/react-router";
import { ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import {
  getIdentity,
  getLegalVersions,
  requestEmailCode,
  verifyEmailCode,
  type LegalVersions,
} from "@/lib/api/auth";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Passwordless sign-in: request a code, then enter it. New emails create an account,
 * and only after the required Terms of Service and Privacy Policy are accepted.
 */
export function EmailCodeForm({ mode }: { mode: "sign-in" | "sign-up" }) {
  const navigate = useNavigate();
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [legal, setLegal] = useState<LegalVersions | null>(null);
  const [termsOk, setTermsOk] = useState(false);
  const [privacyOk, setPrivacyOk] = useState(false);
  const [marketingOk, setMarketingOk] = useState(false);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  useEffect(() => {
    if (mode !== "sign-up") return;
    let active = true;
    getLegalVersions()
      .then((versions) => {
        if (active) setLegal(versions);
      })
      .catch(() => {
        if (active) setError("Sign-up is unavailable right now. Please try again shortly.");
      });
    return () => {
      active = false;
    };
  }, [mode]);

  const target = () => safeRedirect(new URLSearchParams(window.location.search).get("redirect"));
  const signingUp = mode === "sign-up";
  const acceptanceReady = !signingUp || (termsOk && privacyOk && Boolean(legal?.approved));

  async function sendCode() {
    setError("");
    if (!EMAIL.test(email.trim())) {
      setError("Enter a valid email address.");
      return;
    }
    if (signingUp && name.trim().length < 2) {
      setError("Enter your name.");
      return;
    }
    if (signingUp && !legal?.approved) {
      setError("Sign-up is not available yet.");
      return;
    }
    if (signingUp && !(termsOk && privacyOk)) {
      setError("Accept the Terms of Service and the Privacy Policy to create an account.");
      return;
    }
    setBusy(true);
    try {
      await requestEmailCode({
        email: email.trim(),
        ...(signingUp && { name: name.trim() }),
      });
      setStep("code");
      setCooldown(RESEND_SECONDS);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 429
          ? err.message
          : "We couldn't send a code right now. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    setError("");
    if (!/^\d{6}$/.test(code.trim())) {
      setError("Enter the code from your email.");
      return;
    }
    setBusy(true);
    try {
      await verifyEmailCode({
        email: email.trim(),
        code: code.trim(),
        // Sent with every verification, so an existing account ignores it and a new one
        // is created only with the versions the person was shown.
        ...(signingUp &&
          legal && {
            terms_accepted: termsOk,
            privacy_accepted: privacyOk,
            marketing_consent: marketingOk,
            terms_version: legal.terms_version,
            privacy_version: legal.privacy_version,
          }),
      });
      // Provision the account's organization and default workspace before entering the app.
      await getIdentity();
      navigate({ to: target(), replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError && (err.status === 400 || err.status === 409 || err.status === 503)
          ? err.message
          : "That code is invalid or has expired. Request a new one.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        if (step === "email") void sendCode();
        else void verify();
      }}
    >
      {step === "email" ? (
        <>
          {signingUp && (
            <div className="auth-field">
              <label htmlFor="auth-name">Full name</label>
              <input
                id="auth-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                placeholder="Your full name"
              />
            </div>
          )}
          <div className="auth-field">
            <label htmlFor="auth-email">Email address</label>
            <input
              id="auth-email"
              type="email"
              inputMode="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              aria-invalid={Boolean(error)}
              aria-describedby={error ? "auth-error" : undefined}
            />
          </div>
          {signingUp && (
            <fieldset className="auth-consents">
              <legend className="sr-only">Legal agreements</legend>
              <label className="auth-consent">
                <input
                  type="checkbox"
                  checked={termsOk}
                  onChange={(e) => setTermsOk(e.target.checked)}
                  required
                />
                <span>
                  I agree to the{" "}
                  <a href="/terms" target="_blank" rel="noopener noreferrer">
                    Terms of Service
                  </a>{" "}
                  (required)
                </span>
              </label>
              <label className="auth-consent">
                <input
                  type="checkbox"
                  checked={privacyOk}
                  onChange={(e) => setPrivacyOk(e.target.checked)}
                  required
                />
                <span>
                  I have read the{" "}
                  <a href="/privacy" target="_blank" rel="noopener noreferrer">
                    Privacy Policy
                  </a>{" "}
                  (required)
                </span>
              </label>
              <label className="auth-consent">
                <input
                  type="checkbox"
                  checked={marketingOk}
                  onChange={(e) => setMarketingOk(e.target.checked)}
                />
                <span>Send me product news and offers (optional)</span>
              </label>
            </fieldset>
          )}
          <p className="form-footnote">
            We'll email you a sign-in code. If you're new, this creates your account.
          </p>
        </>
      ) : (
        <>
          <div className="form-feedback" role="status">
            If <strong>{email}</strong> can receive mail, a code is on its way. Enter the code from
            that email to sign in.
          </div>
          <div className="auth-field">
            <label htmlFor="auth-code">Sign-in code</label>
            <input
              id="auth-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={8}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              placeholder="6-digit code"
              aria-invalid={Boolean(error)}
              aria-describedby={error ? "auth-error" : undefined}
              autoFocus
            />
          </div>
        </>
      )}
      {error && (
        <p id="auth-error" className="field-error" role="alert">
          {error}
        </p>
      )}
      <Button type="submit" className="auth-submit" disabled={busy || !acceptanceReady}>
        {busy ? <Loader2 className="animate-spin" /> : null}
        {step === "email" ? "Email me a code" : "Sign in"}
        <ArrowRight />
      </Button>
      {step === "code" && (
        <div className="auth-recovery">
          <Button type="button" variant="ghost" disabled={cooldown > 0 || busy} onClick={sendCode}>
            {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setStep("email");
              setCode("");
              setError("");
            }}
          >
            Use a different email
          </Button>
        </div>
      )}
    </form>
  );
}
