const AUTH_PROVIDER = (
  process.env.REACT_APP_AUTH_PROVIDER || "self_hosted"
).toLowerCase();
const COGNITO_DOMAIN = (process.env.REACT_APP_COGNITO_DOMAIN || "").replace(
  /\/$/,
  "",
);
const CLIENT_ID = process.env.REACT_APP_COGNITO_CLIENT_ID || "";
const SIGNOUT_URI =
  process.env.REACT_APP_COGNITO_SIGNOUT_URI || `${window.location.origin}/`;
const REDIRECT_URI =
  process.env.REACT_APP_COGNITO_REDIRECT_URI ||
  `${window.location.origin}/auth/callback`;
const PKCE_VERIFIER_KEY = "oraone_cognito_pkce_verifier";
const OAUTH_STATE_KEY = "oraone_cognito_oauth_state";

export const cognitoEnabled = AUTH_PROVIDER === "cognito";

export function getCognitoLogoutUrl() {
  if (!cognitoEnabled || !COGNITO_DOMAIN || !CLIENT_ID) {
    return null;
  }

  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    logout_uri: SIGNOUT_URI,
  });
  return `${COGNITO_DOMAIN}/logout?${params.toString()}`;
}

export function clearCognitoTransaction() {
  sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  sessionStorage.removeItem(OAUTH_STATE_KEY);
}

function base64Url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

async function sha256(value) {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
}

function randomVerifier() {
  const bytes = new Uint8Array(64);
  crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

function randomState() {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

export async function beginCognitoLogin({ endpoint = "login" } = {}) {
  if (!cognitoEnabled || !COGNITO_DOMAIN || !CLIENT_ID) {
    throw new Error("Cognito login is not configured for this build.");
  }
  if (!["login", "signup", "forgotPassword"].includes(endpoint)) {
    throw new Error("Unsupported Cognito authentication entry point.");
  }
  const verifier = randomVerifier();
  const state = randomState();
  const challenge = base64Url(await sha256(verifier));
  sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
  sessionStorage.setItem(OAUTH_STATE_KEY, state);
  const params = new URLSearchParams({
    client_id: CLIENT_ID,
    response_type: "code",
    scope: "openid email profile",
    redirect_uri: REDIRECT_URI,
    code_challenge_method: "S256",
    code_challenge: challenge,
    state,
  });
  window.location.assign(`${COGNITO_DOMAIN}/${endpoint}?${params.toString()}`);
}

export async function completeCognitoLogin(code, state) {
  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  const expectedState = sessionStorage.getItem(OAUTH_STATE_KEY);
  if (
    !code ||
    !verifier ||
    !expectedState ||
    !state ||
    state !== expectedState
  ) {
    clearCognitoTransaction();
    throw new Error(
      "The Cognito login session is invalid or has expired. Please try again.",
    );
  }
  // Consume the transaction before exchanging the one-time authorization
  // code, so a refresh/replay of the callback cannot reuse the verifier.
  clearCognitoTransaction();
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
  if (!response.ok)
    throw new Error("Cognito authorization could not be completed.");
  return response.json();
}
