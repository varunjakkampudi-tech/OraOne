import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Mail, Lock, KeyRound, ArrowRight, Clock, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";
import { AUTH } from "@/constants/testIds";
import { useSEO } from "@/lib/seo";
import {
  Field,
  IconInput,
  PasswordInput,
  PasswordRulesInline,
  passwordValid,
  OtpInput,
} from "@/components/auth/AuthBits";
import {
  AuthShell,
  GradientButton,
  OrLine,
  OutlineButton,
  IconBadge,
  TipBox,
} from "@/components/auth/AuthShell";

const fmt = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

/* ─────────────────────────────────────────────────────────── */
/* Verify Email — confirm signup with 6-digit Cognito code      */
/* ─────────────────────────────────────────────────────────── */
export function VerifyEmail() {
  useSEO({ title: "Verify Email", description: "Verify your OraOne email address." });
  const { verify, resend, pendingEmail, setPendingEmail } = useAuth();
  const nav = useNavigate();

  const [email, setEmail] = useState(pendingEmail || "");
  const [editingEmail, setEditingEmail] = useState(!pendingEmail);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [resending, setResending] = useState(false);
  const [seconds, setSeconds] = useState(45);

  useEffect(() => {
    if (pendingEmail && pendingEmail !== email) setEmail(pendingEmail);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingEmail]);

  useEffect(() => {
    if (seconds <= 0) return undefined;
    const t = setInterval(() => setSeconds((s) => (s > 0 ? s - 1 : 0)), 1000);
    return () => clearInterval(t);
  }, [seconds]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const res = await verify({ email: email.trim().toLowerCase(), code: code.trim() });
    setBusy(false);
    if (res.ok) {
      toast.success("Email verified!");
      setPendingEmail(null);
      nav("/welcome");
    } else {
      toast.error(res.error || "Verification failed");
    }
  };

  const onResend = async () => {
    if (!email) {
      toast.error("Enter your email first");
      setEditingEmail(true);
      return;
    }
    setResending(true);
    const res = await resend({ email: email.trim().toLowerCase() });
    setResending(false);
    if (res.ok) {
      toast.success("A new code has been sent to your email.");
      setSeconds(45);
    } else {
      toast.error(res.error || "Could not resend code");
    }
  };

  return (
    <AuthShell cardTestId="verify-email-form">
      <IconBadge icon={Mail} check />
      <h1 className="mt-5 text-center text-3xl font-extrabold tracking-tight text-[#0F172A]">
        Verify Your Email
      </h1>
      <p className="mt-2 text-center text-sm leading-relaxed text-[#64748B]">
        We&apos;ve sent a 6-digit verification code to
        <br />
        <span className="font-semibold text-[#2563EB]">{email || "your inbox"}</span>{" "}
        <button
          type="button"
          onClick={() => setEditingEmail((v) => !v)}
          className="font-semibold text-[#2563EB] hover:underline"
        >
          Edit
        </button>
      </p>

      {editingEmail && (
        <div className="mt-4">
          <Field label="Email Address">
            <IconInput
              icon={Mail}
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              data-testid="verify-email-input"
            />
          </Field>
        </div>
      )}

      <form onSubmit={submit} className="mt-7">
        <p className="mb-3 text-sm font-medium text-[#0F172A]">Enter 6-digit code</p>
        <OtpInput value={code} onChange={setCode} length={6} data-testid="verify-code-input" />

        <p className="mt-5 text-center text-sm text-[#64748B]">
          Didn&apos;t receive the code?{" "}
          <button
            type="button"
            onClick={onResend}
            disabled={seconds > 0 || resending}
            data-testid="verify-resend"
            className="font-semibold text-[#2563EB] hover:underline disabled:cursor-not-allowed disabled:text-[#94A3B8] disabled:no-underline"
          >
            {resending ? "Sending..." : "Check your spam folder"}
          </button>
        </p>

        <p className="mt-2 flex items-center justify-center gap-1.5 text-sm text-[#94A3B8]">
          <Clock size={14} />
          {seconds > 0 ? (
            <>
              Resend code in <span className="font-semibold text-[#2563EB]">{fmt(seconds)}</span>
            </>
          ) : (
            <span>You can resend the code now</span>
          )}
        </p>

        <div className="mt-6">
          <GradientButton
            type="submit"
            busy={busy}
            busyLabel="Verifying..."
            disabled={code.length !== 6}
            data-testid="verify-submit"
          >
            Verify Email
          </GradientButton>
        </div>
      </form>

      <p className="mt-6 text-center text-sm text-[#64748B]">
        Wrong email address?{" "}
        <Link to="/signup" className="font-semibold text-[#2563EB] hover:underline">
          Go back
        </Link>
      </p>
    </AuthShell>
  );
}

/* ─────────────────────────────────────────────────────────── */
/* Forgot Password — request a reset code                       */
/* ─────────────────────────────────────────────────────────── */
export function ForgotPassword() {
  useSEO({ title: "Forgot Password", description: "Reset your OraOne password." });
  const { forgotPassword } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const res = await forgotPassword({ email: email.trim().toLowerCase() });
    setBusy(false);
    if (res.ok) {
      toast.success("If the account exists, a reset code has been sent.");
      nav(`/reset-password`);
    } else {
      toast.error(res.error || "Could not start reset");
    }
  };

  return (
    <AuthShell cardTestId="forgot-password-form">
      <IconBadge icon={KeyRound} />
      <h1 className="mt-5 text-center text-3xl font-extrabold tracking-tight text-[#0F172A]">
        Forgot Password?
      </h1>
      <p className="mt-2 text-center text-sm leading-relaxed text-[#64748B]">
        Enter your email and we&apos;ll send you a 6-digit code to reset your password.
      </p>

      <form onSubmit={submit} className="mt-7 space-y-5" noValidate>
        <Field label="Email Address">
          <IconInput
            icon={Mail}
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            data-testid={AUTH.forgotEmail}
          />
        </Field>

        <GradientButton type="submit" busy={busy} busyLabel="Sending..." trailingIcon={ArrowRight} data-testid={AUTH.forgotSubmit}>
          Send Reset Code
        </GradientButton>
      </form>

      <OrLine />

      <OutlineButton to="/login">Back to Sign In</OutlineButton>

      <TipBox icon={ShieldCheck} title="Security Tip">
        Reset codes expire shortly. Request a new one if it doesn&apos;t arrive within a few minutes.
      </TipBox>
    </AuthShell>
  );
}

/* ─────────────────────────────────────────────────────────── */
/* Reset Password — submit code + new password                  */
/* ─────────────────────────────────────────────────────────── */
export function ResetPassword() {
  useSEO({ title: "Reset Password", description: "Set a new OraOne password." });
  const { resetPassword, forgotPassword, pendingEmail, setPendingEmail } = useAuth();
  const nav = useNavigate();

  const [email, setEmail] = useState(pendingEmail || "");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [resending, setResending] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!passwordValid(password)) {
      toast.error("Please choose a stronger password.");
      return;
    }
    if (password !== confirm) {
      toast.error("Passwords don't match");
      return;
    }
    setBusy(true);
    const res = await resetPassword({
      email: email.trim().toLowerCase(),
      code: code.trim(),
      new_password: password,
    });
    setBusy(false);
    if (res.ok) {
      toast.success("Password updated.");
      setPendingEmail(null);
      nav("/welcome");
    } else {
      toast.error(res.error || "Reset failed");
    }
  };

  const resendCode = async () => {
    if (!email) {
      toast.error("Enter your email first");
      return;
    }
    setResending(true);
    const res = await forgotPassword({ email: email.trim().toLowerCase() });
    setResending(false);
    if (res.ok) toast.success("A new verification code has been sent.");
    else toast.error(res.error || "Could not resend code");
  };

  return (
    <AuthShell cardTestId="reset-password-form">
      <IconBadge icon={Lock} />
      <h1 className="mt-5 text-center text-3xl font-extrabold tracking-tight text-[#0F172A]">
        Reset Your Password
      </h1>
      <p className="mt-2 text-center text-sm leading-relaxed text-[#64748B]">
        Enter and confirm your new password
        <br />
        to regain access to your account.
      </p>

      <form onSubmit={submit} className="mt-7 space-y-5" noValidate>
        {!pendingEmail && (
          <Field label="Email">
            <IconInput
              icon={Mail}
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              data-testid="reset-email-input"
            />
          </Field>
        )}

        <Field
          label="Verification Code"
          trailing={
            <button
              type="button"
              onClick={resendCode}
              disabled={resending}
              className="text-xs font-semibold text-[#2563EB] hover:underline disabled:opacity-60"
            >
              {resending ? "Sending..." : "Resend"}
            </button>
          }
        >
          <IconInput
            icon={KeyRound}
            inputMode="numeric"
            required
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            placeholder="6-digit code"
            data-testid="reset-code-input"
          />
        </Field>

        <div>
          <Field label="New Password">
            <PasswordInput
              icon={Lock}
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your new password"
              data-testid={AUTH.resetPassword}
            />
          </Field>
          <PasswordRulesInline value={password} />
        </div>

        <Field label="Confirm New Password">
          <PasswordInput
            icon={Lock}
            required
            minLength={8}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Confirm your new password"
            data-testid="reset-confirm-input"
          />
        </Field>

        <GradientButton type="submit" busy={busy} busyLabel="Saving..." data-testid={AUTH.resetSubmit}>
          Reset Password
        </GradientButton>
      </form>

      <OrLine />

      <OutlineButton to="/login">Back to Sign In</OutlineButton>

      <TipBox icon={ShieldCheck} title="Security Tip">
        Choose a strong password that you don&apos;t use on other websites.
      </TipBox>
    </AuthShell>
  );
}
