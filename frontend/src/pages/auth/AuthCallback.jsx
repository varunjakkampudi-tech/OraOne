import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { clearCognitoTransaction } from "@/lib/cognito";

export default function AuthCallback() {
  const { search } = useLocation();
  const navigate = useNavigate();
  const { completeCognitoSession } = useAuth();
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(search);
    const code = params.get("code");
    const state = params.get("state");
    if (!code) {
      clearCognitoTransaction();
      setError(
        params.get("error_description") || "Cognito sign-in was cancelled.",
      );
      return;
    }
    completeCognitoSession(code, state).then((result) => {
      if (result.ok) navigate("/app/dashboard", { replace: true });
      else setError(result.error || "Could not complete sign-in.");
    });
  }, [search, completeCognitoSession, navigate]);

  if (error)
    return (
      <div className="p-8 text-center text-red-600">
        {error}
        <br />
        <a href="/login">Return to login</a>
      </div>
    );
  return <div className="p-8 text-center">Completing secure sign-in…</div>;
}
