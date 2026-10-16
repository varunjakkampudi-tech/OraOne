import { useState, type FormEvent } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { devLogin, getIdentity } from "@/lib/api/auth";
import { safeRedirect } from "@/lib/auth-redirect";

/**
 * Password sign-in for local development only.
 *
 * This panel is rendered only in development builds (`import.meta.env.DEV`).
 * The API independently refuses the request outside development, so the panel
 * never grants access in a deployed environment.
 */
export function DevSignIn() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await devLogin({ email: email.trim(), password });
      await getIdentity();
      const target = safeRedirect(new URLSearchParams(window.location.search).get("redirect"));
      navigate({ to: target, replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Email or password is incorrect."
          : "Developer sign-in is unavailable. Check that the local API is running.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="dev-sign-in">
      <summary>Developer sign-in (local only)</summary>
      <form noValidate onSubmit={submit} className="dev-sign-in-form">
        <label htmlFor="dev-email">Email</label>
        <input
          id="dev-email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <label htmlFor="dev-password">Password</label>
        <input
          id="dev-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        {error && (
          <p role="alert" className="field-error">
            {error}
          </p>
        )}
        <Button type="submit" variant="outline" disabled={busy}>
          Sign in with password
        </Button>
      </form>
    </details>
  );
}
