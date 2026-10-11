import axios from "axios";
import { cognitoEnabled } from "./cognito";

// Resolve the backend origin. Production builds use same-origin `/api` unless
// an explicit HTTPS API origin is supplied, so a missing build argument can
// never silently point a customer's browser at localhost.
function resolveBackendUrl() {
  const explicit = process.env.REACT_APP_API_URL || process.env.REACT_APP_BACKEND_URL;
  if (explicit) return explicit;

  if (typeof window !== "undefined" && window.location) {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}`;
  }
  return "";
}

const BACKEND_URL = resolveBackendUrl();
export const API_BASE = `${BACKEND_URL}/api`;

const ACCESS_KEY = "oraone_access_token";
const REFRESH_KEY = "oraone_refresh_token";
const PERSIST_KEY = "oraone_auth_persistent";
const ACTIVE_PROJECT_KEY = "oraone_active_project_id";

const safeGet = (storage, key) => {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
};

const safeSet = (storage, key, value) => {
  try {
    storage.setItem(key, value);
  } catch {
    // ignore storage write failures
  }
};

const safeRemove = (storage, key) => {
  try {
    storage.removeItem(key);
  } catch {
    // ignore storage failures
  }
};

export const getToken = () => {
  return safeGet(sessionStorage, ACCESS_KEY) || safeGet(localStorage, ACCESS_KEY);
};

export const getRefreshToken = () => {
  return safeGet(sessionStorage, REFRESH_KEY) || safeGet(localStorage, REFRESH_KEY);
};

export const isPersistentSession = () => safeGet(localStorage, PERSIST_KEY) === "1";

export const setTokens = (access, refresh, { persistent = true } = {}) => {
  const target = persistent ? localStorage : sessionStorage;
  const alternate = persistent ? sessionStorage : localStorage;
  safeSet(target, PERSIST_KEY, persistent ? "1" : "0");
  safeRemove(alternate, ACCESS_KEY);
  safeRemove(alternate, REFRESH_KEY);
  if (access) safeSet(target, ACCESS_KEY, access);
  if (refresh) safeSet(target, REFRESH_KEY, refresh);
};

export const clearTokens = () => {
  safeRemove(localStorage, ACCESS_KEY);
  safeRemove(localStorage, REFRESH_KEY);
  safeRemove(localStorage, PERSIST_KEY);
  safeRemove(sessionStorage, ACCESS_KEY);
  safeRemove(sessionStorage, REFRESH_KEY);
  safeRemove(sessionStorage, PERSIST_KEY);
};

// Active project — the workspace > project layer. Persisted so the chosen
// project survives reloads; attached as X-Project-Id on every API request so
// the backend scopes resources to it.
export const getActiveProjectId = () => safeGet(localStorage, ACTIVE_PROJECT_KEY);

export const setActiveProjectId = (id) => {
  if (id) safeSet(localStorage, ACTIVE_PROJECT_KEY, id);
  else safeRemove(localStorage, ACTIVE_PROJECT_KEY);
};

export const api = axios.create({
  baseURL: API_BASE,
  // Bearer-token auth stays primary (works cross-origin without cookie
  // config), but we also send/receive the httpOnly auth cookies set by the
  // backend (app/core/cookies.py) as defense-in-depth — harmless when the
  // backend doesn't set any, required for the cookie fallback to work.
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Attach Authorization header on every request when we have a token.
api.interceptors.request.use((config) => {
  const t = getToken();
  if (t) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${t}`;
  }
  const pid = getActiveProjectId();
  if (pid) {
    config.headers = config.headers || {};
    config.headers["X-Project-Id"] = pid;
  }
  return config;
});

let refreshInFlight = null;

// Maintenance/outage detection: when the backend is briefly unreachable
// (e.g. during a deploy/restart), we surface a friendly banner instead of
// scary errors and auto-clear once it recovers. Broadcast via window events
// so any component can react without a shared store.
let apiUnavailable = false;
function signalApiUnavailable() {
  if (!apiUnavailable) {
    apiUnavailable = true;
    window.dispatchEvent(new CustomEvent("oraone:api-unavailable"));
  }
}
function signalApiAvailable() {
  if (apiUnavailable) {
    apiUnavailable = false;
    window.dispatchEvent(new CustomEvent("oraone:api-available"));
  }
}

api.interceptors.response.use(
  (response) => {
    signalApiAvailable();
    return response;
  },
  async (error) => {
    const original = error.config || {};
    const status = error.response?.status;

    // No response at all (network error) or a gateway/unavailable status means
    // the API is likely mid-deploy/restart — flag maintenance mode.
    if (!error.response || status === 502 || status === 503 || status === 504) {
      signalApiUnavailable();
    }

    // Normalize error shape: most endpoints raise FastAPI HTTPException
    // ({"detail": ...}), but some return the app's own envelope
    // ({"success": false, "error": {"code", "message"}}). Callers only ever
    // read `err.response.data.detail`, so backfill it here once instead of
    // patching every call site.
    if (error.response?.data && error.response.data.detail === undefined) {
      const envelopeMessage = error.response.data.error?.message;
      if (typeof envelopeMessage === "string") {
        error.response.data.detail = envelopeMessage;
      }
    }

    if (status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    const refreshToken = getRefreshToken();
    if (!refreshToken && !cognitoEnabled) {
      clearTokens();
      return Promise.reject(error);
    }

    original._retry = true;

    try {
      if (!refreshInFlight) {
        refreshInFlight = axios
          .post(
            `${API_BASE}${cognitoEnabled ? "/auth/cognito/refresh" : "/auth/refresh"}`,
            cognitoEnabled ? {} : { refresh_token: refreshToken },
            { headers: { "Content-Type": "application/json" }, withCredentials: true }
          )
          .then(({ data }) => {
            if (cognitoEnabled) return "cookie-session";
            setTokens(data.access_token, data.refresh_token || refreshToken, { persistent: isPersistentSession() });
            return data.access_token;
          })
          .finally(() => {
            refreshInFlight = null;
          });
      }

      const newAccessToken = await refreshInFlight;
      original.headers = original.headers || {};
      if (newAccessToken !== "cookie-session") original.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(original);
    } catch (refreshErr) {
      // Only sign out if the refresh was definitively rejected (the token is
      // no longer valid). A network error / gateway blip (e.g. mid-deploy)
      // must NOT nuke the session — keep the tokens so the request can be
      // retried once the backend is back.
      const refreshStatus = refreshErr?.response?.status;
      if (refreshStatus && refreshStatus !== 502 && refreshStatus !== 503 && refreshStatus !== 504) {
        clearTokens();
      } else {
        signalApiUnavailable();
      }
      return Promise.reject(error);
    }
  }
);

export function formatApiError(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}
