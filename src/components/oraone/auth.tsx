import { useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  ArrowRight,
  ArrowUpRight,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Brand } from "./shell";
import { EmailCodeForm } from "./email-code";
import { DevSignIn } from "./dev-sign-in";
import { validateAuthFields } from "@/lib/phase2";
import previewUrl from "@/assets/oraone-workspace-preview.png";

const descriptions: Record<string, { title: string; text: string; action: string }> = {
  "sign-in": {
    title: "Welcome back",
    text: "Sign in with a one-time code sent to your email. No password needed.",
    action: "email code",
  },
  "sign-up": {
    title: "Create your OraOne account",
    text: "Create your account using a one-time email code.",
    action: "email code",
  },
  "forgot-password": {
    title: "Forgot your password?",
    text: "Enter your account email to request recovery instructions.",
    action: "Request reset link",
  },
  "reset-password": {
    title: "Choose a new password",
    text: "A valid recovery link is required to update your account.",
    action: "Update password",
  },
  "verify-email": {
    title: "Verify your email",
    text: "Enter the code from your verification email to continue.",
    action: "Verify email",
  },
  mfa: {
    title: "A little extra security",
    text: "Enter your six-digit verification code.",
    action: "Verify code",
  },
  callback: {
    title: "Sign-in connection unavailable",
    text: "A verified identity callback is required before your workspace can open.",
    action: "Return to sign in",
  },
  invitation: {
    title: "You’re invited to OraOne",
    text: "Your invitation must be verified before joining a workspace.",
    action: "Sign in to continue",
  },
  "session-expired": {
    title: "Your session has expired",
    text: "Sign in again to securely return to your workspace.",
    action: "Sign in again",
  },
  error: {
    title: "We couldn’t complete sign-in",
    text: "Account access is unavailable. Return to sign in or visit the help center.",
    action: "Return to sign in",
  },
};
export function AuthPage({ title, pagePath }: { title: string; pagePath: string }) {
  const mode = pagePath.split("/").at(-1) || "sign-in";
  const content = descriptions[mode] || {
    title,
    text: "Continue with your OraOne account.",
    action: "Continue",
  };
  const [visible, setVisible] = useState(false);
  const [fields, setFields] = useState({
    name: "",
    email: "",
    password: "",
    confirm: "",
    code: "",
    terms: false,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [feedback, setFeedback] = useState("");
  const formMode = [
    "sign-in",
    "sign-up",
    "forgot-password",
    "reset-password",
    "verify-email",
    "mfa",
  ].includes(mode);
  const setField = (key: string, value: string | boolean) => {
    setFields((previous) => ({ ...previous, [key]: value }));
    setErrors((previous) => ({ ...previous, [key]: "" }));
    setFeedback("");
  };
  const field = (
    key: "name" | "email" | "password" | "confirm" | "code",
    label: string,
    type = "text",
    placeholder = "",
  ) => (
    <div className="auth-field" key={key}>
      <label htmlFor={`auth-${key}`}>{label}</label>
      <div className={key === "password" || key === "confirm" ? "auth-password-wrap" : ""}>
        <input
          id={`auth-${key}`}
          name={key}
          value={fields[key]}
          onChange={(e) => setField(key, e.target.value)}
          type={key === "password" || key === "confirm" ? (visible ? "text" : "password") : type}
          autoComplete={
            key === "email"
              ? "email"
              : key === "name"
                ? "name"
                : key === "code"
                  ? "one-time-code"
                  : mode === "sign-in"
                    ? "current-password"
                    : "new-password"
          }
          inputMode={key === "code" ? "numeric" : key === "email" ? "email" : undefined}
          maxLength={key === "code" ? 6 : undefined}
          placeholder={placeholder}
          aria-invalid={Boolean(errors[key])}
          aria-describedby={errors[key] ? `error-${key}` : undefined}
        />
        {key === "password" && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={visible ? "Hide password" : "Show password"}
            aria-pressed={visible}
            aria-controls="auth-password"
            onClick={() => setVisible(!visible)}
          >
            {visible ? <EyeOff /> : <Eye />}
          </Button>
        )}
      </div>
      {errors[key] && (
        <p id={`error-${key}`} className="field-error" role="alert">
          {errors[key]}
        </p>
      )}
    </div>
  );
  return (
    <div className="phase-auth">
      <header>
        <Link to="/" aria-label="OraOne home">
          <Brand />
        </Link>
        <Link to="/help">
          Need help?
          <ArrowUpRight />
        </Link>
      </header>
      <div className="auth-stage">
        <aside className="auth-editorial" aria-label="OraOne workspace">
          <span className="marketing-eyebrow">YOUR ORAONE WORKSPACE</span>
          <h2>
            More context.
            <br />
            Better conversations.
          </h2>
          <p>Your customers, knowledge and team. One place to bring it all together.</p>
          <img
            src={previewUrl}
            width={1280}
            height={850}
            alt="Sample OraOne dashboard with conversations, assistants and workspace analytics"
            decoding="async"
          />
          <small>Sample workspace · No live customer data</small>
        </aside>
        <main className="phase-auth-main">
          <span className="phase-auth-symbol" aria-hidden="true">
            {mode === "error" ? (
              <TriangleAlert />
            ) : mode.includes("password") || mode === "sign-in" ? (
              <LockKeyhole />
            ) : mode === "verify-email" ? (
              <Mail />
            ) : (
              <ShieldCheck />
            )}
          </span>
          <h1>{content.title}</h1>
          <p className="phase-auth-description">{content.text}</p>
          {Object.values(errors).some(Boolean) && (
            <p className="auth-error-summary" role="alert">
              Check the highlighted fields to continue.
            </p>
          )}
          {mode === "sign-in" || mode === "sign-up" ? (
            <>
              <EmailCodeForm mode={mode} />
              {mode === "sign-in" && import.meta.env.DEV ? <DevSignIn /> : null}
            </>
          ) : !formMode ? (
            <>
              <div className="form-feedback" role="status">
                {mode === "invitation"
                  ? "Invitation details cannot be validated until the identity and membership services are connected. No invitation was accepted."
                  : "The authoritative identity service is not connected in this frontend preview. No session or account changes were made."}
              </div>
              <Button asChild className="auth-submit">
                <Link to="/auth/sign-in">
                  {content.action}
                  <ArrowRight />
                </Link>
              </Button>
            </>
          ) : (
            <form
              noValidate
              onSubmit={(event) => {
                event.preventDefault();
                const nextErrors = validateAuthFields(mode, fields);
                setErrors(nextErrors);
                if (Object.values(nextErrors).some(Boolean)) {
                  const key = Object.keys(nextErrors)[0];
                  if (key) document.getElementById(`auth-${key}`)?.focus();
                  return;
                }
                setFeedback(
                  mode === "reset-password"
                    ? "A valid recovery token and connected identity service are required. Your password has not changed."
                    : "Identity services are not connected. No account, session, email or verification was created.",
                );
              }}
            >
              {mode === "sign-up" && field("name", "Full name", "text", "Your full name")}
              {["sign-in", "sign-up", "forgot-password"].includes(mode) &&
                field("email", "Email address", "email", "you@company.com")}
              {mode === "reset-password" &&
                field(
                  "password",
                  mode === "reset-password" ? "New password" : "Password",
                  "password",
                  "Enter your password",
                )}
              {mode === "reset-password" &&
                field("confirm", "Confirm new password", "password", "Re-enter your password")}
              {["verify-email", "mfa"].includes(mode) &&
                field("code", "Verification code", "text", "6-digit code")}
              {mode === "sign-in" && (
                <div className="phase-auth-options">
                  <Link to="/help">Can’t access your email?</Link>
                </div>
              )}
              {mode === "sign-up" && (
                <div className="auth-consent">
                  <label>
                    <input
                      id="auth-terms"
                      type="checkbox"
                      checked={fields.terms}
                      onChange={(e) => setField("terms", e.target.checked)}
                      aria-invalid={Boolean(errors["terms"])}
                      aria-describedby={errors["terms"] ? "error-terms" : undefined}
                    />
                    <span>
                      I acknowledge the <Link to="/terms">Terms of Service</Link> and{" "}
                      <Link to="/privacy">Privacy Policy</Link>.
                    </span>
                  </label>
                  {errors["terms"] && (
                    <p className="field-error" role="alert" id="error-terms">
                      {errors["terms"]}
                    </p>
                  )}
                </div>
              )}
              {mode === "reset-password" && (
                <div className="form-feedback">
                  Recovery link validation is unavailable. Password policy will follow your
                  configured identity service.
                </div>
              )}
              {["sign-in", "sign-up"].includes(mode) && (
                <div className="form-feedback">
                  Passwordless email code · Email delivery and verification are not connected. No
                  code will be sent.
                </div>
              )}
              <Button type="submit" className="auth-submit">
                Review {content.action.toLowerCase()}
                <ArrowRight />
              </Button>
              {feedback && (
                <div className="form-feedback" role="alert">
                  {feedback}
                </div>
              )}
              {["verify-email", "mfa"].includes(mode) && (
                <div className="auth-recovery">
                  <p>Didn’t receive a code, or has it expired?</p>
                  <Button type="button" variant="ghost" disabled>
                    Resend unavailable
                  </Button>
                  <Link to="/auth/sign-in">Return to sign in</Link>
                </div>
              )}
            </form>
          )}
          <div className="phase-auth-switch">
            {mode === "sign-in" ? (
              <>
                New to OraOne? <Link to="/auth/sign-up">Create an account</Link>
              </>
            ) : (
              <>
                Already have an account? <Link to="/auth/sign-in">Sign in</Link>
              </>
            )}
          </div>
          <div className="phase-auth-preview">
            <span>Just looking? The sample workspace needs no account.</span>
            <Button asChild variant="outline">
              <Link to="/app">
                Explore sample workspace
                <ArrowUpRight />
              </Link>
            </Button>
          </div>
        </main>
      </div>
      <footer>
        <span>© 2026 OraOne</span>
        <div>
          <Link to="/privacy">Privacy</Link>
          <Link to="/terms">Terms</Link>
        </div>
      </footer>
    </div>
  );
}
