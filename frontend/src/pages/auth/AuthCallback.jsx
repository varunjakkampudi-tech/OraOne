import React from "react";
import { Navigate } from "react-router-dom";

/**
 * Legacy route — the app used to redirect here from an AWS Cognito Hosted UI
 * OAuth flow. Auth is now self-hosted (email/password + JWT), so nothing
 * ever navigates here anymore; kept only so an old bookmark/link doesn't
 * 404, bouncing straight to the login page instead.
 */
export default function AuthCallback() {
  return <Navigate to="/login" replace />;
}
