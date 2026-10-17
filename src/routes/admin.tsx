import { createFileRoute, Link, Outlet } from "@tanstack/react-router";
import { useEffect, useState } from "react";

const KEY = "oraone-admin-design-preview";

export const Route = createFileRoute("/admin")({
  validateSearch: (s: Record<string, unknown>): { preview?: "design" } =>
    s["preview"] === "design" ? { preview: "design" } : {},
  head: () => ({
    meta: [{ title: "Admin Console · OraOne" }, { name: "robots", content: "noindex, nofollow" }],
  }),
  component: AdminGate,
});

// The design preview renders sample screens without any sign-in. It exists only for
// local development; production builds always show the restricted notice.
const PREVIEW_ALLOWED = import.meta.env.DEV;

function AdminGate() {
  const { preview } = Route.useSearch();
  const [mode, setMode] = useState<"checking" | "preview" | "locked">("checking");
  useEffect(() => {
    if (!PREVIEW_ALLOWED) {
      sessionStorage.removeItem(KEY);
      setMode("locked");
      return;
    }
    if (preview === "design") sessionStorage.setItem(KEY, "1");
    setMode(sessionStorage.getItem(KEY) === "1" ? "preview" : "locked");
  }, [preview]);

  if (mode === "checking")
    return <main className="container" style={{ padding: "4rem 1rem" }} aria-busy="true" />;
  if (mode === "locked")
    return (
      <main className="container" style={{ maxWidth: 560, padding: "5rem 1rem" }}>
        <h1>Admin Console is restricted</h1>
        <p>
          Staff access must be verified by the OraOne identity service, which is not connected yet.
          No one can open these pages as an administrator.
        </p>
        <p style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 24 }}>
          <Link to="/" className="btn btn-primary">
            Back to home
          </Link>
          {PREVIEW_ALLOWED ? (
            <Link to="/admin" search={{ preview: "design" }} className="btn">
              Open design preview
            </Link>
          ) : null}
        </p>
      </main>
    );
  return (
    <div className="admin-preview-frame">
      <div
        role="status"
        style={{
          background: "var(--warning, #f59e0b)",
          color: "#0F172A",
          padding: "8px 16px",
          fontWeight: 600,
          textAlign: "center",
        }}
      >
        Design preview — not signed in, no admin permissions, all data is sample and actions are
        disabled.{" "}
        <button
          type="button"
          style={{
            textDecoration: "underline",
            background: "none",
            border: 0,
            font: "inherit",
            cursor: "pointer",
          }}
          onClick={() => {
            sessionStorage.removeItem(KEY);
            setMode("locked");
          }}
        >
          Exit preview
        </button>
      </div>
      <Outlet />
    </div>
  );
}
