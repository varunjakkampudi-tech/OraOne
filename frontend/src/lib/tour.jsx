import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "oraone_tour_v1";
// Persistent (survives sessions) — set once the user has seen/auto-run the
// tour so it only ever auto-starts on their very first visit.
const SEEN_KEY = "oraone_tour_seen_v1";
// Module-level guard so the one-shot auto-start survives React 18 StrictMode's
// dev double-mount (which would otherwise clear a scheduled timeout).
let _tourAutoStartScheduled = false;

// A fully guided, Next-driven walkthrough of the whole journey. The user just
// clicks "Next" (or "Skip") — the tour navigates them to each screen, one step
// at a time, and highlights the key element with a short explanation. Steps
// only point at real pages that exist without any data, so it never dead-ends.
//   • route   — page the tour navigates to when this step opens
//   • target  — [data-tour="<id>"] element to spotlight (optional; centered if absent)
//   • cta     — final call-to-action link (last step)
export const TOUR_STEPS = [
  {
    id: "welcome",
    title: "Welcome to OraOne 👋",
    body: "This quick tour shows how to launch your first AI agent — from creating it to putting it live on your website. Click Next to follow along, or Skip anytime.",
    route: "/app/dashboard",
  },
  {
    id: "create-agent",
    title: "Step 1 — Create an agent",
    body: "Everything starts with this button. It opens a short, guided builder where you set up a chat agent.",
    route: "/app/dashboard",
    target: "create-agent",
  },
  {
    id: "nav-agents",
    title: "Step 2 — Your agents live here",
    body: "All the agents you create appear on this page. Open any one to edit it, test it, or grab its embed code.",
    route: "/app/agents",
    target: "nav-agents",
  },
  {
    id: "nav-knowledge",
    title: "Step 3 — Add your knowledge",
    body: "Upload documents or add your website here so the agent answers from YOUR content. Tip: put your website URL on the agent and we auto-crawl it into knowledge the moment you deploy.",
    route: "/app/knowledge-base",
    target: "nav-knowledge",
  },
  {
    id: "nav-conversations",
    title: "Step 4 — Watch conversations",
    body: "Every chat your agent has with a customer shows up here live, and captured leads flow into Leads automatically.",
    route: "/app/conversations",
    target: "nav-conversations",
  },
  {
    id: "deploy-explain",
    title: "Step 5 — Test, then go live",
    body: "Open your agent and choose “Review & Deploy”. Hit “Test widget” to try it instantly (no website needed), then copy the one-line snippet onto your site to go live.",
    route: "/app/agents",
  },
  {
    id: "done",
    title: "You're ready! 🎉",
    body: "That's the whole journey: Create → Add knowledge → Test → Deploy. Let's create your first agent now.",
    route: "/app/dashboard",
    cta: { label: "Create my agent", to: "/app/agents/new" },
  },
];

const TourContext = createContext(null);

function loadState() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return { active: false, index: 0 };
    const parsed = JSON.parse(raw);
    return { active: !!parsed.active, index: Number(parsed.index) || 0 };
  } catch {
    return { active: false, index: 0 };
  }
}

function saveState(s) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  } catch {
    /* ignore */
  }
}

export function TourProvider({ children }) {
  const [state, setState] = useState(loadState);

  const persist = useCallback((s) => {
    saveState(s);
    return s;
  }, []);

  const start = useCallback(() => {
    try { localStorage.setItem(SEEN_KEY, "1"); } catch { /* ignore */ }
    setState(persist({ active: true, index: 0 }));
  }, [persist]);
  const exit = useCallback(() => setState(persist({ active: false, index: 0 })), [persist]);
  const next = useCallback(
    () => setState((s) => persist({ ...s, index: Math.min(s.index + 1, TOUR_STEPS.length - 1) })),
    [persist]
  );
  const back = useCallback(
    () => setState((s) => persist({ ...s, index: Math.max(s.index - 1, 0) })),
    [persist]
  );

  const value = useMemo(
    () => ({ ...state, total: TOUR_STEPS.length, start, exit, next, back }),
    [state, start, exit, next, back]
  );

  // Auto-run the tour once for brand-new users on their first dashboard visit.
  // Marks "seen" only when it actually starts; the module-level guard keeps it
  // to a single fire even under StrictMode. The delay lets targets mount first.
  useEffect(() => {
    if (_tourAutoStartScheduled) return;
    let seen = true;
    try { seen = localStorage.getItem(SEEN_KEY) === "1"; } catch { /* ignore */ }
    if (seen) return;
    _tourAutoStartScheduled = true;
    setTimeout(() => {
      try { localStorage.setItem(SEEN_KEY, "1"); } catch { /* ignore */ }
      setState((s) => (s.active ? s : persist({ active: true, index: 0 })));
    }, 900);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <TourContext.Provider value={value}>{children}</TourContext.Provider>;
}

export function useTour() {
  const ctx = useContext(TourContext);
  if (!ctx) throw new Error("useTour must be used within a TourProvider");
  return ctx;
}
