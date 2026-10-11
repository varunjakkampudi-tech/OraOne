import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { api, formatApiError, setTokens, clearTokens, getToken, getRefreshToken } from "./api";

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
    role: profile.role || "owner",
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
    if (!getToken()) {
      clearIdentity();
      return { ok: false, error: "Not signed in." };
    }

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
  }, [clearIdentity]);

  const fetchMe = useCallback(async () => {
    if (!getToken()) {
      setUser(false);
      clearIdentity();
      setLoading(false);
      return;
    }

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
        // Transient failure (backend restarting / network blip) but we still
        // hold a token — DON'T log the user out. Render from cached identity
        // so a deploy window doesn't kick everyone to the login screen; live
        // calls recover automatically once the API is back.
        const cached = loadIdentityFromStorage();
        if (cached?.user) setUser(normalizeUser(cached.user));
        else setUser(false);
      } else {
        setUser(false);
        clearIdentity();
      }
    } finally {
      setLoading(false);
    }
  }, [fetchIdentity, clearIdentity]);

  useEffect(() => {
    if (!getToken()) {
      setUser(false);
      clearIdentity();
      setLoading(false);
      return;
    }

    fetchMe();
  }, [fetchMe, clearIdentity]);

  const _err = (e) =>
    formatApiError(e?.response?.data?.detail) || e?.message || "Something went wrong.";

  const login = useCallback(async ({ email, password } = {}) => {
    const normalizedEmail = String(email || "").trim().toLowerCase();
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

      setTokens(data.access_token, data.refresh_token ?? null, { persistent: true });
      await fetchMe();
      const identityResult = await fetchIdentity();
      if (!identityResult.ok) {
        return { ok: true, identityError: identityResult.error };
      }
      return { ok: true, identity: identityResult.identity };
    } catch (e) {
      return { ok: false, error: _err(e) };
    }
  }, [fetchMe, fetchIdentity]);

  const verifyLoginOtp = useCallback(async ({ email, code } = {}) => {
    try {
      const { data } = await api.post("/auth/login/verify-otp", { email, code });
      setTokens(data.access_token, data.refresh_token ?? null, { persistent: true });
      await fetchMe();
      // Block resolution on identity so the caller can redirect *only after*
      // user + organization context are ready (Phase 4 requirement #6).
      const identityResult = await fetchIdentity();
      if (!identityResult.ok) {
        return { ok: true, identityError: identityResult.error };
      }
      return { ok: true, identity: identityResult.identity };
    } catch (e) {
      return { ok: false, error: _err(e) };
    }
  }, [fetchMe, fetchIdentity]);

  const signup = useCallback(async ({ email, password, name } = {}) => {
    const normalizedEmail = String(email || "").trim().toLowerCase();
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
        message: data?.message || "Signup successful. Please verify your email if prompted, then log in.",
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
    try {
      if (getToken()) {
        const refreshToken = getRefreshToken();
        await api.post("/auth/logout", refreshToken ? { refresh_token: refreshToken } : {});
      }
    } catch {
      // Best-effort logout; always clear local session.
    }

    clearTokens();
    setUser(false);
    clearIdentity();
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

  const changePassword = useCallback(async ({ current_password, new_password }) => {
    try {
      await api.post("/auth/change-password", { current_password, new_password });
      return { ok: true };
    } catch (e) {
      return { ok: false, error: _err(e) };
    }
  }, []);

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
