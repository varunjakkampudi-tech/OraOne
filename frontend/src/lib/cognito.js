const AUTH_PROVIDER = (process.env.REACT_APP_AUTH_PROVIDER || "self_hosted").toLowerCase();
const COGNITO_DOMAIN = (process.env.REACT_APP_COGNITO_DOMAIN || "").replace(/\/$/, "");
const CLIENT_ID = process.env.REACT_APP_COGNITO_CLIENT_ID || "";
const REDIRECT_URI = process.env.REACT_APP_COGNITO_REDIRECT_URI || `${window.location.origin}/auth/callback`;
const PKCE_VERIFIER_KEY = "oraone_cognito_pkce_verifier";

export const cognitoEnabled = AUTH_PROVIDER === "cognito";

function base64Url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sha256(value) {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
}

function randomVerifier() {
  const bytes = new Uint8Array(64);
  crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

export async function beginCognitoLogin() {
  if (!cognitoEnabled || !COGNITO_DOMAIN || !CLIENT_ID) {
    throw new Error("Cognito login is not configured for this build.");
  }
  const verifier = randomVerifier();
  const challenge = base64Url(await sha256(verifier));
  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    response_type: "code",
    scope: "openid email profile",
    redirect_uri: REDIRECT_URI,
    code_challenge_method: "S256",
    code_challenge: challenge,
  });
  window.location.assign(`${COGNITO_DOMAIN}/oauth2/authorize?${params.toString()}`);
}

export async function completeCognitoLogin(code) {
  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  if (!code || !verifier) throw new Error("The Cognito login session has expired. Please try again.");
  const response = await fetch(`${COGNITO_DOMAIN}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: CLIENT_ID,
      code,
      redirect_uri: REDIRECT_URI,
      code_verifier: verifier,
    }),
  });
  sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  if (!response.ok) throw new Error("Cognito authorization could not be completed.");
  return response.json();
}
