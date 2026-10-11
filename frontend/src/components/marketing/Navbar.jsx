import React, { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Logo } from "./Logo";
import { NAV } from "@/constants/testIds";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/lib/auth";

const links = [
  { to: "/products", label: "Products", id: NAV.productsMenu },
  { to: "/solutions", label: "Solutions", id: NAV.solutionsMenu },
  { to: "/integrations", label: "Integrations", id: NAV.integrationsLink },
  { to: "/templates", label: "Templates", id: NAV.templatesLink },
  { to: "/pricing", label: "Pricing", id: NAV.pricingLink },
  { to: "/about", label: "Company", id: NAV.companyMenu },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const location = useLocation();
  const { login, signup } = useAuth();

  const openAuth = (mode) => {
    setAuthMode(mode);
    setError("");
    setInfo("");
    setAuthOpen(true);
  };

  const closeAuth = () => {
    setAuthOpen(false);
    setBusy(false);
    setError("");
    setInfo("");
    const params = new URLSearchParams(location.search);
    if (params.has("auth")) {
      params.delete("auth");
      nav(
        {
          pathname: location.pathname,
          search: params.toString() ? `?${params.toString()}` : "",
        },
        { replace: true }
      );
    }
  };

  useEffect(() => {
    const query = new URLSearchParams(location.search).get("auth");
    if (query === "login" || query === "signup") {
      openAuth(query);
    }
  }, [location.search]);

  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setInfo("");

    if (!email.trim() || !password) {
      setError("Please enter email and password.");
      return;
    }
    if (authMode === "signup" && !name.trim()) {
      setError("Please enter your name.");
      return;
    }
    if (authMode === "signup" && password !== confirmPassword) {
      setError("Password and confirm password do not match.");
      return;
    }

    setBusy(true);
    const action = authMode === "signup" ? signup : login;
    const res =
      authMode === "signup"
        ? await action({ email, password, name })
        : await action({ email, password });
    setBusy(false);

    if (!res?.ok) {
      setError(res?.error || "Authentication failed.");
      return;
    }

    if (authMode === "signup") {
      setInfo(res?.message || "Signup successful. Please verify your email if required, then log in.");
      setAuthMode("login");
      return;
    }

    closeAuth();
    nav("/app/dashboard");
  };

  return (
    <header className="fixed top-0 inset-x-0 z-40">
      <div className="border-b border-[#E2E8F0]/60 bg-white/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="h-16 flex items-center justify-between gap-2 sm:gap-4">
            <Link to="/" className="flex-shrink-0 flex items-center" data-testid="navbar-brand-link">
              <Logo className="h-9 sm:h-10 w-auto object-contain" />
            </Link>

            <nav className="hidden lg:flex items-center gap-1">
              {links.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  data-testid={l.id}
                  className={({ isActive }) =>
                    `text-sm font-medium px-3.5 py-2 rounded-lg transition-colors ${
                      isActive
                        ? "text-[#2563EB] bg-[#EFF6FF]"
                        : "text-[#475569] hover:text-[#0F172A] hover:bg-[#F8FAFC]"
                    }`
                  }
                >
                  {l.label}
                </NavLink>
              ))}
            </nav>

            <div className="flex items-center gap-2">
              <button
                data-testid={NAV.loginBtn}
                onClick={() => nav("/login")}
                className="hidden sm:inline-flex items-center text-sm font-medium text-[#475569] hover:text-[#0F172A] px-3 py-2"
              >
                Login
              </button>
              <button
                data-testid={NAV.bookDemoBtn}
                onClick={() => nav("/contact")}
                className="hidden sm:inline-flex items-center text-sm font-medium text-[#0F172A] bg-white border border-[#E2E8F0] hover:bg-[#F8FAFC] px-4 py-2 rounded-xl transition-colors"
              >
                Book Demo
              </button>
              <button
                data-testid={NAV.startFreeBtn}
                onClick={() => nav("/signup")}
                className="inline-flex items-center text-sm font-medium text-white bg-[#2563EB] hover:bg-[#1D4ED8] px-3 sm:px-4 py-2 rounded-xl transition-all shadow-[0_4px_14px_-2px_rgba(37,99,235,0.45)] hover:shadow-[0_6px_20px_-2px_rgba(37,99,235,0.55)] hover:-translate-y-0.5"
              >
                Start Free
              </button>
              <button
                data-testid={NAV.mobileToggle}
                onClick={() => setOpen(!open)}
                className="lg:hidden p-2 rounded-lg text-[#0F172A] hover:bg-[#F1F5F9]"
                aria-label={open ? "Close menu" : "Open menu"}
                aria-expanded={open}
                aria-controls="mobile-menu"
              >
                {open ? <X size={20} /> : <Menu size={20} />}
              </button>
            </div>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {open && (
          <motion.div
            id="mobile-menu"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="lg:hidden bg-white border-b border-[#E2E8F0] shadow-lg"
          >
            <nav aria-label="Mobile" className="px-4 py-3 flex flex-col">
              {links.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  onClick={() => setOpen(false)}
                  className="py-3 text-[#0F172A] text-base font-medium"
                >
                  {l.label}
                </NavLink>
              ))}
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  nav("/login");
                }}
                className="py-3 text-left text-[#0F172A] text-base font-medium"
              >
                Login
              </button>
              <Link
                to="/contact"
                onClick={() => setOpen(false)}
                className="mt-2 inline-flex items-center justify-center px-4 py-3 rounded-xl text-sm font-semibold text-[#0F172A] bg-white border border-[#E2E8F0]"
              >
                Book Demo
              </Link>
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  nav("/signup");
                }}
                className="mt-2 inline-flex items-center justify-center px-4 py-3 rounded-xl text-sm font-semibold text-white bg-[#2563EB] shadow-[0_4px_14px_-2px_rgba(37,99,235,0.45)]"
              >
                Start Free
              </button>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {authOpen && (
          <motion.div
            className="fixed inset-0 z-[90]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="absolute inset-0 bg-[#0F172A]/55" onClick={closeAuth} />
            <div className="absolute inset-0 p-4 sm:p-6 grid place-items-center">
              <motion.div
                role="dialog"
                aria-modal="true"
                aria-label="Authentication"
                initial={{ opacity: 0, y: 18, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.98 }}
                transition={{ duration: 0.2 }}
                className="relative w-full max-w-md rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-2xl"
              >
                <button
                  type="button"
                  aria-label="Close"
                  onClick={closeAuth}
                  className="absolute right-3 top-3 p-2 rounded-lg text-[#64748B] hover:bg-[#F1F5F9]"
                >
                  <X size={18} />
                </button>

                <div className="flex items-center gap-2 mb-4">
                  <button
                    type="button"
                    onClick={() => {
                      setAuthMode("login");
                      setError("");
                      setInfo("");
                    }}
                    className={`px-3 py-1.5 rounded-lg text-sm font-semibold ${
                      authMode === "login" ? "bg-[#EFF6FF] text-[#2563EB]" : "text-[#64748B]"
                    }`}
                  >
                    Login
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setAuthMode("signup");
                      setError("");
                      setInfo("");
                    }}
                    className={`px-3 py-1.5 rounded-lg text-sm font-semibold ${
                      authMode === "signup" ? "bg-[#EFF6FF] text-[#2563EB]" : "text-[#64748B]"
                    }`}
                  >
                    Sign Up
                  </button>
                </div>

                <h3 className="text-xl font-bold text-[#0F172A]">
                  {authMode === "signup" ? "Create your account" : "Welcome back"}
                </h3>
                <p className="mt-1 text-sm text-[#64748B]">
                  Enter your email and password. Passwords are hashed with Argon2 on the backend.
                </p>

                <form className="mt-5 space-y-3" onSubmit={handleAuthSubmit}>
                  {authMode === "signup" && (
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Full Name"
                      className="w-full rounded-xl border border-[#E2E8F0] px-4 py-3 text-sm text-[#0F172A] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/15 focus:border-[#2563EB]"
                    />
                  )}
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Email"
                    className="w-full rounded-xl border border-[#E2E8F0] px-4 py-3 text-sm text-[#0F172A] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/15 focus:border-[#2563EB]"
                  />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Password"
                    className="w-full rounded-xl border border-[#E2E8F0] px-4 py-3 text-sm text-[#0F172A] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/15 focus:border-[#2563EB]"
                  />
                  {authMode === "signup" && (
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm Password"
                      className="w-full rounded-xl border border-[#E2E8F0] px-4 py-3 text-sm text-[#0F172A] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/15 focus:border-[#2563EB]"
                    />
                  )}

                  {error && <p className="text-sm text-[#DC2626]">{error}</p>}
                  {info && <p className="text-sm text-[#2563EB]">{info}</p>}

                  <button
                    type="submit"
                    disabled={busy}
                    className="w-full rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-semibold py-3 transition-colors disabled:opacity-60"
                  >
                    {busy ? "Checking..." : authMode === "signup" ? "Sign Up" : "Login"}
                  </button>
                </form>

                <p className="mt-4 text-xs text-[#64748B]">
                  New user? Sign up with your email and we'll verify it.
                </p>
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
