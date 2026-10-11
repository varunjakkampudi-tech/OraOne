import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Mail, Lock, ArrowRight, ShieldCheck } from "lucide-react";
import { useSEO } from "@/lib/seo";
import { useAuth } from "@/lib/auth";
import { Field, IconInput, PasswordInput, Checkbox, OtpInput } from "@/components/auth/AuthBits";
import { AuthShell, GradientButton } from "@/components/auth/AuthShell";

export default function Login() {
  useSEO({ title: "Login", description: "Sign in to your OraOne account" });
  const { login, verifyLoginOtp } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [otpStep, setOtpStep] = useState(false);
  const [code, setCode] = useState("");

  const afterSignIn = (res) => {
    if (res.identityError) {
      setError(`Signed in, but we couldn't load your workspace: ${res.identityError}. Please retry in a moment.`);
      return;
    }
    nav("/app/dashboard", { replace: true });
  };

  const handleSignIn = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    const res = await login({ email, password });
    setBusy(false);
    if (!res?.ok) {
      setError(res?.error || "Login failed.");
      return;
    }
    if (res.otpRequired) {
      setOtpStep(true);
      return;
    }
    afterSignIn(res);
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    const res = await verifyLoginOtp({ email, code });
    setBusy(false);
    if (!res?.ok) {
      setError(res?.error || "Incorrect or expired code.");
      return;
    }
    afterSignIn(res);
  };

  if (otpStep) {
    return (
      <AuthShell cardTestId="login-otp-form">
        <h1 className="text-center text-3xl font-extrabold tracking-tight text-[#0F172A]">Check your email</h1>
        <p className="mt-2 text-center text-sm text-[#64748B]">
          We sent a 6-digit code to <span className="font-semibold text-[#2563EB]">{email}</span>
        </p>

        <form className="mt-8 space-y-5" onSubmit={handleVerifyOtp}>
          <div>
            <p className="mb-3 text-sm font-medium text-[#0F172A]">Enter 6-digit code</p>
            <OtpInput value={code} onChange={setCode} length={6} data-testid="login-otp-input" />
          </div>

          {error && <p className="text-sm text-[#DC2626]">{error}</p>}

          <GradientButton
            type="submit"
            busy={busy}
            busyLabel="Verifying..."
            trailingIcon={ShieldCheck}
            data-testid="login-otp-submit"
          >
            Verify &amp; sign in
          </GradientButton>

          <button
            type="button"
            onClick={() => {
              setOtpStep(false);
              setCode("");
              setError("");
            }}
            className="w-full text-center text-sm font-semibold text-[#2563EB] hover:underline"
          >
            Back to sign in
          </button>
        </form>
      </AuthShell>
    );
  }

  return (
    <AuthShell cardTestId="login-form">
      <h1 className="text-center text-3xl font-extrabold tracking-tight text-[#0F172A]">Welcome Back</h1>
      <p className="mt-2 text-center text-sm text-[#64748B]">
        Sign in to continue managing your AI agents.
      </p>

      <form className="mt-8 space-y-5" onSubmit={handleSignIn}>
        <Field label="Email">
          <IconInput
            icon={Mail}
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            data-testid="login-email-input"
          />
        </Field>

        <Field label="Password">
          <PasswordInput
            icon={Lock}
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            data-testid="login-password-input"
          />
        </Field>

        <div className="flex items-center justify-between">
          <Checkbox
            id="remember-me"
            checked={remember}
            onChange={setRemember}
            accentClass="peer-checked:border-[#2563EB] peer-checked:bg-[#2563EB] peer-focus-visible:ring-[#2563EB]/15"
            data-testid="login-remember"
          >
            Remember me
          </Checkbox>
          <Link to="/forgot-password" className="text-sm font-semibold text-[#2563EB] hover:underline">
            Forgot Password?
          </Link>
        </div>

        {error && <p className="text-sm text-[#DC2626]">{error}</p>}

        <GradientButton
          type="submit"
          busy={busy}
          busyLabel="Signing in..."
          trailingIcon={ArrowRight}
          data-testid="login-submit"
        >
          Continue
        </GradientButton>
      </form>

      <p className="mt-6 text-center text-sm text-[#64748B]">
        New to OraOne?{" "}
        <Link to="/signup" className="font-semibold text-[#2563EB] hover:underline">
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}
