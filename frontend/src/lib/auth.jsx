import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
} from "react";
import {
  api,
  formatApiError,
  setTokens,
  clearTokens,
  getToken,
  getRefreshToken,
} from "./api";
import { cognitoEnabled, completeCognitoLogin } from "./cognito";

const AuthContext = createContext(null);

const IDENTITY_KEY = "oraone_identity";

function normalizeUser(profile) {
  if (!profile) return false;
  return {
    ...profile,
    id: profile.id || profile.userId || "",
    userId: profile.userId || profile.id || "",
    email: profile.email || "",
    name: profile.name || profile.full_name || "",
    full_name: profile.full_name || profile.name || "",
    role: profile.role || profile.platform_role || "user",
    platformRole: profile.platform_role || profile.role || "user",
  };
}

// ---------------- Identity (Phase 4) ----------------
const safeStorageGet = (key) => {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
};
const safeStorageSet = (key, value) => {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
};
const safeStorageRemove = (key) => {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore */
  }
};

function loadIdentityFromStorage() {
  const raw = safeStorageGet(IDENTITY_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed && parsed.user && parsed.organization && parsed.membership) {
      return parsed;
    }
    return null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null=checking, false=out, object=in
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Phase 4 — organization + membership context
  const initialIdentity = loadIdentityFromStorage();
  const [identity, setIdentity] = useState(initialIdentity); // { user, organization, membership, is_new_user } | null
  const [identityLoading, setIdentityLoading] = useState(false);
  const [identityError, setIdentityError] = useState(null);
  const identityInFlight = useRef(null);

  // Temporary email state for signup/recovery flows (not persisted in URL for privacy)
  const [pendingEmail, setPendingEmail] = useState(null);

  const clearIdentity = useCallback(() => {
    setIdentity(null);
    setIdentityError(null);
    safeStorageRemove(IDENTITY_KEY);
  }, []);

  const fetchIdentity = useCallback(async () => {
    if (identityInFlight.current) {
      return identityInFlight.current;
    }

    setIdentityLoading(true);
    setIdentityError(null);

    const promise = (async () => {
      try {
        const { data } = await api.get("/auth/identity");
        setIdentity(data);
        safeStorageSet(IDENTITY_KEY, JSON.stringify(data));
        return { ok: true, identity: data };
      } catch (e) {
        const msg =
          formatApiError(e?.response?.data?.detail) ||
          e?.message ||
          "Could not load your workspace.";
        setIdentityError(msg);
        return { ok: false, error: msg };
      } finally {
        setIdentityLoading(false);
        identityInFlight.current = null;
      }
    })();

    identityInFlight.current = promise;
    return promise;
  }, []);

  const fetchMe = useCallback(async () => {
    setLoading(true);
    setAuthError(null);
    try {
      // /auth/me and /auth/identity are independent, token-only calls and the
      // dashboard needs both — fire them together instead of serially so the
      // app becomes interactive ~one round-trip sooner.
      const mePromise = api.get("/auth/me");
      fetchIdentity();
      const { data } = await mePromise;
      setUser(normalizeUser(data));
    } catch (e) {
      const status = e?.response?.status;
      if (status === 401) {
        // Genuinely unauthenticated (expired/invalid token) — sign out.
        clearTokens();
        setUser(false);
        clearIdentity();
      } else if (getToken()) {
        // A cached identity is display data only. Never establish an
        // authenticated or authorized UI state from attacker-modifiable
        // browser storage when the authoritative API is unavailable.
        setUser(false);
        clearIdentity();
        setAuthError(
          status === 429
            ? "Too many requests. Wait a moment, then retry your session."
            : "We could not verify your session. Check your connection and retry.",
        );
      } else {
        setUser(false);
        clearIdentity();
      }
    } finally {
      setLoading(false);
    }
  }, [fetchIdentity, clearIdentity]);

  useEffect(() => {
    if (!getToken() && !cognitoEnabled) {
      setUser(false);
      clearIdentity();
      setLoading(false);
      return;
    }
    fetchMe();
  }, [fetchMe, clearIdentity]);

  const _err = (e) =>
    formatApiError(e?.response?.data?.detail) ||
    e?.message ||
    "Something went wrong.";

  const clearEstablishedSession = useCallback(async () => {
    // Cognito session establishment sets an httpOnly cookie that JavaScript
    // cannot remove. Revoke/clear it server-side before exposing a failed
    // identity result to the caller.
    try {
      await api.post(cognitoEnabled ? "/auth/cognito/logout" : "/auth/logout");
    } catch {
      // Local state is still cleared below; the server endpoint is best effort
      // when the identity failure was caused by a transient backend outage.
    }
    clearTokens();
    clearIdentity();
    setUser(false);
  }, [clearIdentity]);

  const login = useCallback(
    async ({ email, password, persistent = false } = {}) => {
      const normalizedEmail = String(email || "")
        .trim()
        .toLowerCase();
      const normalizedPassword = String(password || "");

      if (!normalizedEmail || !normalizedPassword) {
        return { ok: false, error: "Please enter both email and password." };
      }

      try {
        const { data } = await api.post("/auth/login", {
          email: normalizedEmail,
          password: normalizedPassword,
        });

        // Password verified — a one-time code was emailed. Sign-in completes
        // in verifyLoginOtp() once the caller submits that code.
        if (data?.otp_required) {
          setPendingEmail(normalizedEmail);
          return { ok: true, otpRequired: true, email: normalizedEmail };
        }

        setTokens(data.access_token, data.refresh_token ?? null, {
          persistent,
        });
        await fetchMe();
        const identityResult = await fetchIdentity();
        if (!identityResult.ok) {
          await clearEstablishedSession();
          return {
            ok: false,
            error: identityResult.error || "Could not load account identity.",
          };
        }
        return { ok: true, identity: identityResult.identity };
      } catch (e) {
        return { ok: false, error: _err(e) };
      }
    },
    [fetchMe, fetchIdentity, clearEstablishedSession],
  );

  const completeCognitoSession = useCallback(
    async (code, state) => {
      if (!cognitoEnabled)
        return { ok: false, error: "Cognito authentication is not enabled." };
      try {
        const tokens = await completeCognitoLogin(code, state);
        await api.post("/auth/cognito/session", {
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token,
        });
        // A first Cognito login has no application user row until identity
        // provisioning commits. Loading /me beforehand races that transaction.
        const identityResult = await fetchIdentity();
        if (!identityResult.ok) {
          await clearEstablishedSession();
          return {
            ok: false,
            error: identityResult.error || "Could not load account identity.",
          };
        }
        await fetchMe();
        return { ok: true, identity: identityResult.identity };
      } catch (e) {
        return { ok: false, error: _err(e) };
      }
    },
    [fetchMe, fetchIdentity, clearEstablishedSession],
  );

  const verifyLoginOtp = useCallback(
    async ({ email, code, persistent = false } = {}) => {
      try {
        const { data } = await api.post("/auth/login/verify-otp", {
          email,
          code,
        });
        setTokens(data.access_token, data.refresh_token ?? null, {
          persistent,
        });
        await fetchMe();
        // Block resolution on identity so the caller can redirect *only after*
        // user + organization context are ready (Phase 4 requirement #6).
        const identityResult = await fetchIdentity();
        if (!identityResult.ok) {
          await clearEstablishedSession();
          return {
            ok: false,
            error: identityResult.error || "Could not load account identity.",
          };
        }
        return { ok: true, identity: identityResult.identity };
      } catch (e) {
        return { ok: false, error: _err(e) };
      }
    },
    [fetchMe, fetchIdentity, clearEstablishedSession],
  );

  const signup = useCallback(async ({ email, password, name } = {}) => {
    const normalizedEmail = String(email || "")
      .trim()
      .toLowerCase();
    const normalizedPassword = String(password || "");
    const normalizedName = String(name || "").trim();

    if (!normalizedName) {
      return { ok: false, error: "Please enter your name." };
    }
    if (!normalizedEmail || !normalizedPassword) {
      return { ok: false, error: "Please enter email and password." };
    }

    try {
      const { data } = await api.post("/auth/signup", {
        email: normalizedEmail,
        password: normalizedPassword,
        name: normalizedName,
      });
      setPendingEmail(normalizedEmail);
      return {
        ok: true,
        message:
          data?.message ||
          "Signup successful. Please verify your email if prompted, then log in.",
      };
    } catch (e) {
      return { ok: false, error: _err(e) };
    }
  }, []);

  const verify = useCallback(async ({ email, code }) => {
    try {
      await api.post("/auth/verify", { email, code });
      return { ok: true };
    } catch (e) {
      return { ok: false, error: _err(e) };
    }
  }, []);

  const resend = useCallback(async ({ email }) => {
    try {
      await api.post("/auth/resend", { email });
      return { ok: true };
    } catch (e) {
      return { ok: false, error: _err(e) };
    }
  }, []);

  const forgotPassword = useCallback(async ({ email }) => {
    try {
      await api.post("/auth/forgot-password", { email });
      setPendingEmail(email);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: _err(e) };
    }
  }, []);

  const resetPassword = useCallback(async ({ email, code, new_password }) => {
    try {
      await api.post("/auth/reset-password", { email, code, new_password });
      return { ok: true };
    } catch (e) {
      return { ok: false, error: _err(e) };
    }
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken();
    const shouldRevoke = cognitoEnabled || Boolean(getToken());

    // Clear the browser session before waiting on the network. A stalled or
    // unavailable revoke endpoint must never leave a usable local session.
    clearTokens();
    setUser(false);
    clearIdentity();

    try {
      // Cognito browser sessions intentionally keep tokens out of JS storage;
      // the httpOnly refresh cookie is the session indicator. Always call the
      // provider logout endpoint in Cognito mode so that cookie is revoked.
      if (shouldRevoke) {
        await api.post(
          cognitoEnabled ? "/auth/cognito/logout" : "/auth/logout",
          cognitoEnabled
            ? {}
            : refreshToken
              ? { refresh_token: refreshToken }
              : {},
        );
      }
    } catch {
      // Best-effort logout; always clear local session.
    }
  }, [clearIdentity]);

  const logoutAll = useCallback(async () => {
    try {
      if (getToken()) {
        await api.post("/auth/logout-all");
      }
    } finally {
      // Always drop the local session even if the revoke call failed —
      // the user asked to sign out, and staying "logged in" locally after
      // that request would be worse than a stale server-side token.
      clearTokens();
      setUser(false);
      clearIdentity();
    }
  }, [clearIdentity]);

  const updateProfile = useCallback(async ({ full_name }) => {
    try {
      const { data } = await api.patch("/auth/profile", { full_name });
      setUser(normalizeUser(data));
      return { ok: true };
    } catch (e) {
      return { ok: false, error: _err(e) };
    }
  }, []);

  const changePassword = useCallback(
    async ({ current_password, new_password }) => {
      try {
        await api.post("/auth/change-password", {
          current_password,
          new_password,
        });
        return { ok: true };
      } catch (e) {
        return { ok: false, error: _err(e) };
      }
    },
    [],
  );

  const refresh = fetchMe;
  const refreshSession = fetchMe;
  const getCurrentUser = fetchMe;
  const isAuthenticated = !!user;

  // Phase 4 — convenience accessors (read-only views into identity)
  const organization = identity?.organization || null;
  const membership = identity?.membership || null;
  const organizationId = organization?.id || null;
  const organizationName = organization?.name || null;
  const membershipRole = membership?.role || null;

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        authError,
        isAuthenticated,
        // Phase 4
        identity,
        organization,
        membership,
        organizationId,
        organizationName,
        membershipRole,
        identityLoading,
        identityError,
        fetchIdentity,
        pendingEmail,
        setPendingEmail,
        // existing
        signup,
        verify,
        resend,
        login,
        completeCognitoSession,
        verifyLoginOtp,
        forgotPassword,
        resetPassword,
        logout,
        logoutAll,
        updateProfile,
        changePassword,
        refresh,
        refreshSession,
        getCurrentUser,
        fetchMe,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
