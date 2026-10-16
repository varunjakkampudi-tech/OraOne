import { useEffect, useState } from "react";
import { RESEND_SECONDS, safeRedirect } from "@/lib/auth-redirect";
import { useNavigate } from "@tanstack/react-router";
import { ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { requestEmailCode, verifyEmailCode, getIdentity } from "@/lib/api/auth";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Real passwordless sign-in: request a code, then enter it. New emails create an account. */
export function EmailCodeForm({ mode }: { mode: "sign-in" | "sign-up" }) {
  const navigate = useNavigate();
  const [step, setStep] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const target = () => safeRedirect(new URLSearchParams(window.location.search).get("redirect"));

  async function sendCode() {
    setError("");
    if (!EMAIL.test(email.trim())) {
      setError("Enter a valid email address.");
      return;
    }
    if (mode === "sign-up" && name.trim().length < 2) {
      setError("Enter your name.");
      return;
    }
    setBusy(true);
    try {
      await requestEmailCode({
        email: email.trim(),
        ...(mode === "sign-up" && { name: name.trim() }),
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
      await verifyEmailCode({ email: email.trim(), code: code.trim() });
      // Provision the account's organization and default workspace before entering the app.
      await getIdentity();
      navigate({ to: target(), replace: true });
    } catch {
      setError("That code is invalid or has expired. Request a new one.");
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
          {mode === "sign-up" && (
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
      <Button type="submit" className="auth-submit" disabled={busy}>
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
