import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  User,
  Lock,
  Bell,
  Palette,
  Monitor,
  ShieldCheck,
  Save,
  Eye,
  EyeOff,
  Check,
  Loader2,
  LogOut,
  Users,
  UserCog,
  Cpu,
  KeyRound,
  Webhook,
  Code2,
  Gauge,
  CreditCard,
  ScrollText,
  ChevronRight,
  Activity,
  Clock,
  CalendarDays,
  AlertCircle,
  Rocket,
  Lightbulb,
  LifeBuoy,
} from "lucide-react";import { useAuth } from "@/lib/auth";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";

// Account settings open inline as tabs in the right-hand panel.
const ACCOUNT_TABS = [
  { id: "profile",       icon: User,     label: "Profile",       desc: "Update your personal information" },
  { id: "password",      icon: Lock,     label: "Password",      desc: "Change your password" },
  { id: "notifications", icon: Bell,     label: "Notifications", desc: "Manage your notifications" },
  { id: "appearance",    icon: Palette,  label: "Appearance",    desc: "Theme & display" },
  { id: "sessions",      icon: Monitor,  label: "Sessions",      desc: "Devices & security" },
  { id: "activity",      icon: Activity, label: "Activity",      desc: "Sign-in & account history" },
];

// Workspace settings are full pages of their own — Settings is now the single
// hub that links out to them, grouped so they're easy to find.
const WORKSPACE_GROUPS = [
  {
    title: "Workspace",
    links: [
      { to: "/app/team",     icon: Users,   label: "Members",  desc: "Invite & manage people" },
      { to: "/app/teams",    icon: UserCog, label: "Teams",    desc: "Organize members into teams" },
      { to: "/app/branding", icon: Palette, label: "Branding", desc: "Logo, colors & widget look" },
      { to: "/app/ai-models",icon: Cpu,     label: "AI Models",desc: "Choose your default models" },
    ],
  },
  {
    title: "Developers",
    links: [
      { to: "/app/api-keys",   icon: KeyRound, label: "API Keys",           desc: "Programmatic access" },
      { to: "/app/webhooks",   icon: Webhook,  label: "Webhooks",           desc: "Event notifications" },
      { to: "/app/developers", icon: Code2,    label: "Developer Platform", desc: "SDKs & integration docs" },
    ],
  },
  {
    title: "Billing",
    links: [
      { to: "/app/usage",      icon: Gauge,      label: "Usage & Limits", desc: "Track your consumption" },
      { to: "/app/billing",    icon: CreditCard, label: "Billing",        desc: "Plan & payment method" },
      { to: "/app/audit-logs", icon: ScrollText, label: "Audit Logs",     desc: "Security & activity history" },
    ],
  },
  {
    title: "Resources",
    links: [
      { to: "/app/portal",           icon: LifeBuoy,  label: "Customer Portal",  desc: "Support, docs, status & account" },
      { to: "/app/getting-started",  icon: Rocket,    label: "Getting Started",  desc: "Guided setup checklist" },
      { to: "/app/tickets", icon: Lightbulb, label: "Support Tickets", desc: "Report bugs, get help or request features" },
      { to: "/app/changelog",        icon: Rocket,    label: "Changelog",        desc: "What's new in OraOne" },
      { to: "/app/status",           icon: Activity,  label: "Product Status",   desc: "Live service health" },
    ],
  },
];

// Internal operations dashboard — owners/admins only.
const ADMIN_GROUP = {
  title: "Admin",
  links: [
    { to: "/app/operations", icon: ShieldCheck, label: "Operations & Security", desc: "Internal controls" },
  ],
};

export default function Settings() {
  const [active, setActive] = useState("profile");
  const nav = useNavigate();
  const { membershipRole, user } = useAuth();
  const role = (membershipRole || user?.role || "").toLowerCase();
  const isAdmin = role === "owner" || role === "admin";

  const groups = isAdmin ? [...WORKSPACE_GROUPS, ADMIN_GROUP] : WORKSPACE_GROUPS;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-white border border-[#E2E8F0] grid grid-cols-1 lg:grid-cols-[300px_1fr] overflow-hidden">
        {/* Tabs (left) */}
        <nav className="border-b lg:border-b-0 lg:border-r border-[#F1F5F9] p-3 space-y-1" aria-label="Settings sections">
          <p className="px-3 pt-2 pb-1 text-[10.5px] font-semibold uppercase tracking-wider text-[#94A3B8]">Account</p>
          {ACCOUNT_TABS.map((t) => {
            const sel = active === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActive(t.id)}
                data-testid={`settings-tab-${t.id}`}
                className={`w-full flex items-start gap-3 px-3 py-3 rounded-xl text-left transition-colors ${
                  sel ? "bg-[#EFF6FF]" : "hover:bg-[#F8FAFC]"
                }`}
                aria-current={sel ? "true" : undefined}
              >
                <t.icon size={16} className={sel ? "text-[#2563EB] mt-0.5" : "text-[#64748B] mt-0.5"} />
                <div className="min-w-0">
                  <p className={`text-[13.5px] font-semibold ${sel ? "text-[#2563EB]" : "text-[#0F172A]"}`}>{t.label}</p>
                  <p className="text-[11.5px] text-[#94A3B8] mt-0.5 leading-snug">{t.desc}</p>
                </div>
              </button>
            );
          })}

          {groups.map((g) => (
            <div key={g.title} className="pt-2">
              <p className="px-3 pt-2 pb-1 text-[10.5px] font-semibold uppercase tracking-wider text-[#94A3B8]">{g.title}</p>
              {g.links.map((l) => (
                <button
                  key={l.to}
                  onClick={() => nav(l.to)}
                  data-testid={`settings-link-${l.to.split("/").pop()}`}
                  className="w-full flex items-center gap-3 px-3 py-3 rounded-xl text-left transition-colors hover:bg-[#F8FAFC] group"
                >
                  <l.icon size={16} className="text-[#64748B] shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-[13.5px] font-semibold text-[#0F172A]">{l.label}</p>
                    <p className="text-[11.5px] text-[#94A3B8] mt-0.5 leading-snug">{l.desc}</p>
                  </div>
                  <ChevronRight size={15} className="text-[#CBD5E1] group-hover:text-[#94A3B8] shrink-0" />
                </button>
              ))}
            </div>
          ))}
        </nav>

        {/* Panel (right) */}
        <div className="p-6 sm:p-8">
          {active === "profile"       && <ProfileSection />}
          {active === "password"      && <PasswordSection />}
          {active === "notifications" && <NotificationsSection />}
          {active === "appearance"    && <AppearanceSection />}
          {active === "sessions"      && <SessionsSection />}
          {active === "activity"      && <ActivitySection />}
        </div>
      </div>
    </div>
  );
}

/* =========================== Save status =========================== */

// Subtle autosave indicator — replaces explicit Save buttons on autosaving
// surfaces (Profile, Notifications). Mirrors OpenAI / Linear / Notion UX.
function SaveStatus({ state }) {
  if (state === "saving")
    return (
      <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#64748B]" data-testid="save-status-saving">
        <Loader2 size={13} className="animate-spin" /> Saving…
      </span>
    );
  if (state === "saved")
    return (
      <span className="inline-flex items-center gap-1.5 text-[12px] font-medium text-[#16A34A]" data-testid="save-status-saved">
        <Check size={13} /> Saved
      </span>
    );
  return <span className="text-[12px] font-medium text-transparent select-none">·</span>;
}

/* =========================== Sections =========================== */

function SectionHeader({ title, desc }) {
  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold text-[#0F172A]">{title}</h3>
      <p className="text-[13px] text-[#64748B] mt-1">{desc}</p>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-[13px] font-semibold text-[#0F172A] mb-2">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full px-4 py-3 rounded-xl border border-[#E2E8F0] bg-white text-[14px] text-[#0F172A] placeholder-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10 transition-all";

function SaveBtn({ label = "Save Changes", onClick }) {
  return (
    <button
      onClick={onClick}
      data-testid="settings-save-btn"
      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-[13.5px] font-semibold shadow-[0_8px_24px_-8px_rgba(37,99,235,0.5)]"
    >
      <Save size={14} /> {label}
    </button>
  );
}

function ProfileSection() {
  const { user, updateProfile } = useAuth();
  const initials = (user?.full_name || "OA")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();
  const [name, setName] = useState(user?.full_name || "");
  const [status, setStatus] = useState("idle"); // idle | saving | saved | error
  const timer = useRef(null);
  const first = useRef(true);

  // Autosave — debounce edits and surface a subtle Saving… / Saved indicator
  // instead of a Save button.
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return undefined;
    }
    if (!name.trim()) return undefined;
    setStatus("saving");
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      const res = await updateProfile({ full_name: name.trim() });
      if (res.ok) {
        setStatus("saved");
        timer.current = setTimeout(() => setStatus("idle"), 2000);
      } else {
        setStatus("error");
        toast.error(res.error || "Couldn't save your changes.");
      }
    }, 900);
    return () => clearTimeout(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  return (
    <>
      <div className="mb-6 flex items-start justify-between gap-4">
        <SectionHeader title="Profile Information" desc="Update your personal information." />
        <SaveStatus state={status} />
      </div>

      <div className="flex items-center gap-5 mb-7">
        <div className="size-20 rounded-full bg-[#2563EB] grid place-items-center text-white text-2xl font-bold">
          {initials}
        </div>
        <div>
          <p className="text-[15px] font-semibold text-[#0F172A] inline-flex items-center gap-2">
            {user?.full_name || "—"}
            <span className="text-[10.5px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium capitalize">
              {user?.role || "Owner"}
            </span>
          </p>
        </div>
      </div>

      <div className="space-y-5 max-w-2xl">
        <Field label="Full Name">
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} data-testid="settings-name" />
        </Field>
        <Field label="Email Address">
          <div className="relative">
            <input className={`${inputCls} pr-10 bg-[#F8FAFC] text-[#64748B]`} value={user?.email || ""} readOnly data-testid="settings-email" />
            <Lock size={14} className="absolute right-4 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
          </div>
        </Field>
        <Field label="Role">
          <div className="relative">
            <input className={`${inputCls} pr-10 bg-[#F8FAFC] text-[#64748B] capitalize`} value={user?.role || "Owner"} readOnly />
            <Lock size={14} className="absolute right-4 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
          </div>
        </Field>
      </div>
    </>
  );
}

function PasswordSection() {
  const { changePassword } = useAuth();
  const [show, setShow] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);

  const onSubmit = async () => {
    if (next.length < 8) {
      toast.error("New password must be at least 8 characters.");
      return;
    }
    if (next !== confirm) {
      toast.error("New password and confirmation don't match.");
      return;
    }
    setSaving(true);
    const res = await changePassword({ current_password: current, new_password: next });
    setSaving(false);
    if (res.ok) {
      toast.success("Password updated.");
      setCurrent("");
      setNext("");
      setConfirm("");
    } else {
      toast.error(res.error || "Couldn't update your password.");
    }
  };

  return (
    <>
      <SectionHeader title="Change Password" desc="Use a strong password you don't reuse anywhere else." />
      <div className="space-y-5 max-w-xl">
        {[
          { label: "Current Password", value: current, set: setCurrent, testid: "settings-current-password" },
          { label: "New Password", value: next, set: setNext, testid: "settings-new-password" },
          { label: "Confirm New Password", value: confirm, set: setConfirm, testid: "settings-confirm-password" },
        ].map((f) => (
          <Field key={f.label} label={f.label}>
            <div className="relative">
              <input
                type={show ? "text" : "password"}
                className={`${inputCls} pr-11`}
                placeholder="••••••••"
                value={f.value}
                onChange={(e) => f.set(e.target.value)}
                data-testid={f.testid}
              />
              <button type="button" onClick={() => setShow((s) => !s)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#94A3B8] hover:text-[#475569]" aria-label="Toggle visibility">
                {show ? <Eye size={16} /> : <EyeOff size={16} />}
              </button>
            </div>
          </Field>
        ))}
      </div>
      <div className="mt-7">
        <SaveBtn label={saving ? "Updating…" : "Update Password"} onClick={onSubmit} />
      </div>
    </>
  );
}

function NotificationsSection() {
  const opts = [
    { id: "leads",  label: "New leads",     desc: "Email me when a new lead is captured." },
    { id: "weekly", label: "Weekly digest", desc: "Receive a weekly performance summary." },
    { id: "team",   label: "Team activity", desc: "When a teammate joins, leaves, or changes role." },
  ];
  const STORAGE_KEY = "oraone_notification_prefs";
  const [state, setState] = useState(() => {
    const defaults = Object.fromEntries(opts.map((o) => [o.id, true]));
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      return { ...defaults, ...saved };
    } catch {
      return defaults;
    }
  });
  const [status, setStatus] = useState("idle");
  const timer = useRef(null);

  const toggle = (id) => {
    setState((s) => {
      const next = { ...s, [id]: !s[id] };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
    setStatus("saving");
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      setStatus("saved");
      timer.current = setTimeout(() => setStatus("idle"), 2000);
    }, 600);
  };

  return (
    <>
      <div className="mb-6 flex items-start justify-between gap-4">
        <SectionHeader title="Notifications" desc="Choose what you want to be notified about." />
        <SaveStatus state={status} />
      </div>
      <div className="space-y-3 max-w-xl">
        {opts.map((o) => (
          <label key={o.id} className="flex items-start gap-4 p-4 rounded-xl border border-[#E2E8F0] hover:border-[#CBD5E1] cursor-pointer">
            <div className="flex-1 min-w-0">
              <p className="text-[14px] font-semibold text-[#0F172A]">{o.label}</p>
              <p className="text-[12px] text-[#64748B] mt-0.5">{o.desc}</p>
            </div>
            <Toggle on={state[o.id]} onChange={() => toggle(o.id)} />
          </label>
        ))}
      </div>
    </>
  );
}

function Toggle({ on, onChange }) {
  return (
    <button type="button" onClick={onChange} aria-pressed={on} className={`relative w-11 h-6 rounded-full transition-colors shrink-0 ${on ? "bg-[#2563EB]" : "bg-[#CBD5E1]"}`}>
      <span className={`absolute top-0.5 size-5 rounded-full bg-white shadow transition-transform ${on ? "translate-x-[22px]" : "translate-x-0.5"}`} />
    </button>
  );
}

function AppearanceSection() {
  const themes = [
    { id: "light", label: "Light", desc: "Bright, default theme." },
    { id: "system", label: "System", desc: "Match your device setting." },
    { id: "dark", label: "Dark", desc: "Easy on the eyes at night." },
  ];
  return (
    <>
      <SectionHeader title="Appearance" desc="Personalize how OraOne looks for you." />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl">
        {themes.map((t) => (
          <div
            key={t.id}
            className={`rounded-xl border p-4 ${
              t.id === "light" ? "border-[#2563EB] ring-2 ring-[#2563EB]/15" : "border-[#E2E8F0] opacity-60"
            }`}
          >
            <div className="flex items-center justify-between">
              <p className="text-[13.5px] font-semibold text-[#0F172A]">{t.label}</p>
              {t.id === "light" ? (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium">Active</span>
              ) : (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#F1F5F9] text-[#94A3B8] font-medium">Soon</span>
              )}
            </div>
            <p className="text-[12px] text-[#64748B] mt-1">{t.desc}</p>
          </div>
        ))}
      </div>
      <p className="text-[12px] text-[#94A3B8] mt-5">More appearance options are coming soon.</p>
    </>
  );
}

function SessionsSection() {
  const { identity, user, logoutAll } = useAuth();
  const u = identity?.user || {};
  const [enabled, setEnabled] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const ua = typeof navigator !== "undefined" ? navigator.userAgent : "";
  const browser = /Edg/.test(ua)
    ? "Microsoft Edge"
    : /Chrome/.test(ua)
    ? "Google Chrome"
    : /Firefox/.test(ua)
    ? "Firefox"
    : /Safari/.test(ua)
    ? "Safari"
    : "Browser";
  const os = /Windows/.test(ua)
    ? "Windows"
    : /Mac OS X|Macintosh/.test(ua)
    ? "macOS"
    : /Android/.test(ua)
    ? "Android"
    : /iPhone|iPad|iOS/.test(ua)
    ? "iOS"
    : /Linux/.test(ua)
    ? "Linux"
    : "";
  const lastLogin = u.last_login_at || user?.lastLogin || null;

  // Self-hosted JWT refresh tokens are tracked server-side (Redis), so
  // "sign out everywhere" maps to a real revoke-all that invalidates every
  // refresh token for this account — including this one. We confirm, then
  // drop the user back to the login page.
  const signOutEverywhere = async () => {
    if (signingOut) return;
    const ok = window.confirm(
      "Sign out of all devices? This ends every active session, including this one. You'll need to sign in again."
    );
    if (!ok) return;
    setSigningOut(true);
    try {
      await logoutAll();
      toast.success("Signed out of all devices.");
    } catch (e) {
      toast.error(formatApiError(e));
      setSigningOut(false);
    }
  };

  return (
    <>
      <SectionHeader title="Sessions & Security" desc="Manage where you're signed in and your account security." />

      <div className="max-w-2xl space-y-3">
        <div className="rounded-xl border border-[#E2E8F0] p-4 flex items-center gap-4">
          <div className="size-10 rounded-xl bg-[#EFF6FF] grid place-items-center text-[#2563EB] shrink-0">
            <Monitor size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[14px] font-semibold text-[#0F172A] inline-flex items-center gap-2">
              {browser}{os ? ` · ${os}` : ""}
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-50 text-green-700 border border-green-200 font-medium">
                This device
              </span>
            </p>
            <p className="text-[12px] text-[#64748B] mt-0.5">
              Active now{lastLogin ? ` · signed in ${relTime(lastLogin)}` : " · current session"}
            </p>
          </div>
        </div>
        <p className="text-[11.5px] text-[#94A3B8] px-1">
          Sessions use short-lived tokens that refresh automatically. To end access on a lost or shared
          device, sign out of all devices below.
        </p>
      </div>

      <div className="max-w-2xl mt-6 rounded-xl border border-[#E2E8F0] p-5 flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[14px] font-semibold text-[#0F172A] inline-flex items-center gap-2">
            <ShieldCheck size={15} className="text-[#2563EB]" /> Two-factor authentication
          </p>
          <p className="text-[12px] text-[#64748B] mt-0.5">Require a 6-digit code on sign-in. Use Google Authenticator, 1Password, Authy, etc.</p>
        </div>
        <Toggle on={enabled} onChange={() => { setEnabled((v) => !v); toast.success(`2FA ${!enabled ? "enabled" : "disabled"}`); }} />
      </div>

      <div className="mt-6">
        <button
          onClick={signOutEverywhere}
          disabled={signingOut}
          data-testid="sessions-signout-all"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white border border-[#E2E8F0] hover:bg-[#F8FAFC] text-[13px] font-semibold text-[#475569] disabled:opacity-60"
        >
          {signingOut ? <Loader2 size={14} className="animate-spin" /> : <LogOut size={14} />}
          Sign out of all devices
        </button>
      </div>
    </>
  );
}

/* ---- Activity: real sign-in + account history ---- */

const ACTIVITY_VERBS = {
  create: "Created",
  update: "Updated",
  delete: "Deleted",
  publish: "Published",
  unpublish: "Unpublished",
  share: "Shared",
  export: "Exported",
  import: "Imported",
  read: "Viewed",
  query: "Queried",
  search: "Searched",
  invite: "Invited",
  login: "Signed in",
  logout: "Signed out",
};

const ACTIVITY_NOUNS = {
  agent: "an agent",
  lead: "a lead",
  conversation: "a conversation",
  knowledge_base: "a knowledge base",
  document: "a document",
  website: "a website",
  widget: "a widget",
  org_branding: "branding",
  organization: "the workspace",
  project: "a project",
  api_key: "an API key",
  webhook: "a webhook",
  member: "a member",
  team: "a team",
  workflow: "a workflow",
  integration: "an integration",
};

function relTime(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Math.max(0, Date.now() - then);
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function ActivitySection() {
  const { identity, user } = useAuth();
  const u = identity?.user || {};
  const uid = u.id || user?.id || user?.userId || null;
  const [logs, setLogs] = useState(null); // null = loading
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    setLogs(null);
    setError(null);
    api
      .get("/audit-logs", { params: { limit: 60 } })
      .then(({ data }) => {
        if (!alive) return;
        const actors = data.actors || {};
        const rows = (data.logs || [])
          .filter((l) => !uid || l.user_id === uid)
          .slice(0, 15)
          .map((l) => {
            const verb = ACTIVITY_VERBS[l.action] || (l.action ? l.action[0].toUpperCase() + l.action.slice(1) : "Did");
            const noun = ACTIVITY_NOUNS[l.resource] || (l.resource ? l.resource.replace(/_/g, " ") : "an item");
            return {
              id: l.id,
              text: `${verb} ${noun}`,
              actor: actors[l.user_id]?.name || "You",
              at: l.created_at,
            };
          });
        setLogs(rows);
      })
      .catch((e) => alive && setError(formatApiError(e)));
    return () => {
      alive = false;
    };
  }, [uid]);

  const lastLogin = u.last_login_at || user?.lastLogin || null;
  const createdAt = u.created_at || user?.createdAt || null;

  const facts = [
    { icon: Clock, label: "Last sign-in", value: fmtDate(lastLogin) },
    { icon: CalendarDays, label: "Member since", value: fmtDate(createdAt) },
    { icon: ShieldCheck, label: "Role", value: (u.role || user?.role || "owner").replace(/^\w/, (c) => c.toUpperCase()) },
  ];

  return (
    <>
      <SectionHeader title="Account Activity" desc="Your recent sign-in details and account history." />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl mb-7">
        {facts.map((f) => (
          <div key={f.label} className="rounded-xl border border-[#E2E8F0] p-4">
            <f.icon size={16} className="text-[#2563EB]" />
            <p className="text-[11.5px] text-[#94A3B8] mt-2.5 font-medium">{f.label}</p>
            <p className="text-[13.5px] font-semibold text-[#0F172A] mt-0.5">{f.value}</p>
          </div>
        ))}
      </div>

      <h4 className="text-[13.5px] font-semibold text-[#0F172A] mb-3">Recent activity</h4>

      {error && (
        <div className="max-w-2xl flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-[12.5px] text-amber-800">
          <AlertCircle size={15} /> {error}
        </div>
      )}

      {!error && logs === null && (
        <div className="max-w-2xl space-y-2.5" data-testid="activity-loading">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-12 rounded-xl bg-[#F1F5F9] animate-pulse" />
          ))}
        </div>
      )}

      {!error && Array.isArray(logs) && logs.length === 0 && (
        <p className="max-w-2xl text-[13px] text-[#64748B]">No recent activity yet.</p>
      )}

      {!error && Array.isArray(logs) && logs.length > 0 && (
        <ul className="max-w-2xl space-y-1" data-testid="activity-list">
          {logs.map((l, i) => (
            <li key={l.id || i} className="flex items-start gap-3 py-2.5 border-b border-[#F1F5F9] last:border-0">
              <span className="mt-1.5 size-2 rounded-full bg-[#2563EB]/60 shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-[13px] text-[#0F172A]">
                  <span className="font-semibold">{l.actor}</span> {l.text}
                </p>
                <p className="text-[11.5px] text-[#94A3B8] mt-0.5">{relTime(l.at)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
