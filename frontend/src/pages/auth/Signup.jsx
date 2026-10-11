import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { User, Mail, Building2, Lock, ArrowRight } from "lucide-react";
import { useSEO } from "@/lib/seo";
import { useAuth } from "@/lib/auth";
import {
  Field,
  IconInput,
  PasswordInput,
  PasswordRulesInline,
  passwordValid,
  Checkbox,
} from "@/components/auth/AuthBits";
import { AuthShell, GradientButton } from "@/components/auth/AuthShell";

export default function Signup() {
  useSEO({ title: "Sign up", description: "Create your OraOne account in minutes." });
  const { signup } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [company, setCompany] = useState("");
  const [agree, setAgree] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const canSubmit =
    name.trim() && email.trim() && passwordValid(password) && password === confirm && agree && !busy;

  const handleSignUp = async (e) => {
    e.preventDefault();
    setError("");
    if (!agree) {
      setError("Please agree to the Terms of Service and Privacy Policy.");
      return;
    }
    if (!passwordValid(password)) {
      setError("Please choose a stronger password.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords don't match.");
      return;
    }
    setBusy(true);
    const res = await signup({ email, password, name });
    setBusy(false);

    if (!res?.ok) {
      setError(res?.error || "Signup failed.");
      return;
    }

    if (company) {
      try {
        const biz = JSON.parse(sessionStorage.getItem("onboard_business") || "{}");
        sessionStorage.setItem("onboard_business", JSON.stringify({ ...biz, company_name: company }));
      } catch {
        sessionStorage.setItem("onboard_business", JSON.stringify({ company_name: company }));
      }
    }

    nav(`/verify-email`, { replace: true });
  };

  return (
    <AuthShell cardMaxWidth="max-w-lg" cardTestId="signup-form">
      <h1 className="text-center text-3xl font-extrabold tracking-tight text-[#0F172A]">
        Create Your Account
      </h1>
      <p className="mt-2 text-center text-sm text-[#64748B]">
        Get started with OraOne in just a few steps.
      </p>

      <form className="mt-8 space-y-5" onSubmit={handleSignUp}>
        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="Full Name">
            <IconInput
              icon={User}
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your full name"
              data-testid="signup-name-input"
            />
          </Field>

          <Field label="Work Email">
            <IconInput
              icon={Mail}
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              data-testid="signup-email-input"
            />
          </Field>
        </div>

        <div>
          <Field label="Password">
            <PasswordInput
              icon={Lock}
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Create a strong password"
              data-testid="signup-password-input"
            />
          </Field>
          <PasswordRulesInline value={password} />
        </div>

        <Field label="Confirm Password">
          <PasswordInput
            icon={Lock}
            required
            minLength={8}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Confirm your password"
            data-testid="signup-confirm-input"
          />
        </Field>

        <Field label={<>Company Name <span className="font-normal text-[#64748B]">(Optional)</span></>}>
          <IconInput
            icon={Building2}
            type="text"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Enter your company name"
            data-testid="signup-company-input"
          />
        </Field>

        <Checkbox
          id="signup-terms"
          checked={agree}
          onChange={setAgree}
          accentClass="peer-checked:border-[#2563EB] peer-checked:bg-[#2563EB] peer-focus-visible:ring-[#2563EB]/15"
          data-testid="signup-terms"
        >
          I agree to the{" "}
          <Link to="/terms" className="font-semibold text-[#2563EB] hover:underline">Terms of Service</Link>{" "}
          and{" "}
          <Link to="/privacy" className="font-semibold text-[#2563EB] hover:underline">Privacy Policy</Link>
        </Checkbox>

        {error && <p className="text-sm text-[#DC2626]">{error}</p>}

        <GradientButton
          type="submit"
          disabled={!canSubmit}
          busy={busy}
          busyLabel="Creating account..."
          trailingIcon={ArrowRight}
          data-testid="signup-submit"
        >
          Create Account
        </GradientButton>
      </form>

      <p className="mt-6 text-center text-sm text-[#64748B]">
        Already have an account?{" "}
        <Link to="/login" className="font-semibold text-[#2563EB] hover:underline">Sign in</Link>
      </p>
    </AuthShell>
  );
}
