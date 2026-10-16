import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Building2,
  ChartNoAxesCombined,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  FileText,
  Flag,
  KeyRound,
  Layers,
  LockKeyhole,
  Menu,
  Network,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Users,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Brand } from "./shell";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { products } from "@/lib/oraone";

const sections = [
  { name: "Overview", path: "/admin", icon: Layers, group: "PLATFORM" },
  { name: "Users", path: "/admin/users", icon: Users, group: "PLATFORM" },
  { name: "Organizations", path: "/admin/organizations", icon: Building2, group: "PLATFORM" },
  { name: "Products", path: "/admin/products", icon: Layers, group: "PLATFORM" },
  { name: "Free access", path: "/admin/subscriptions", icon: CreditCard, group: "COMMERCIAL" },
  { name: "Access & usage", path: "/admin/billing", icon: CreditCard, group: "COMMERCIAL" },
  { name: "Usage", path: "/admin/usage", icon: ChartNoAxesCombined, group: "COMMERCIAL" },
  { name: "AI providers", path: "/admin/ai-models", icon: Network, group: "OPERATIONS" },
  { name: "Infrastructure", path: "/admin/infrastructure", icon: Network, group: "OPERATIONS" },
  { name: "Monitoring", path: "/admin/monitoring", icon: Activity, group: "OPERATIONS" },
  { name: "Errors", path: "/admin/errors", icon: Activity, group: "OPERATIONS" },
  { name: "Audit logs", path: "/admin/audit", icon: FileText, group: "OPERATIONS" },
  { name: "Support", path: "/admin/support", icon: Users, group: "OPERATIONS" },
  { name: "Feature flags", path: "/admin/feature-flags", icon: Flag, group: "CONTROL" },
  { name: "Entitlements", path: "/admin/entitlements", icon: KeyRound, group: "CONTROL" },
  { name: "Security", path: "/admin/security", icon: ShieldCheck, group: "CONTROL" },
  { name: "Settings", path: "/admin/settings", icon: Settings, group: "CONTROL" },
];
const tableDefinitions: Record<string, { columns: string[]; text: string; filters: string[] }> = {
  users: {
    columns: ["User", "Platform role", "Account status", "Organizations", "Last activity"],
    text: "User records require verified platform access and the identity directory service.",
    filters: ["All statuses", "Active", "Suspended"],
  },
  organizations: {
    columns: ["Organization", "Workspaces", "Members", "Access", "Last activity"],
    text: "Organization records require server-verified platform access and organization APIs.",
    filters: ["All organizations", "Active", "Archived"],
  },
  subscriptions: {
    columns: ["Organization", "Plan", "Status", "Billing period", "Renewal"],
    text: "Subscription data and approved commercial plans are not connected.",
    filters: ["All statuses", "Active", "Past due", "Canceled"],
  },
  billing: {
    columns: ["Invoice", "Organization", "Amount", "Payment status", "Issued"],
    text: "No invoices or transactions are available without a connected billing service.",
    filters: ["All statuses", "Paid", "Open", "Overdue"],
  },
  usage: {
    columns: ["Workspace", "Product", "AI usage", "Consumption", "Period"],
    text: "Usage records require authorized metering APIs. No financial or consumption metrics are fabricated.",
    filters: ["All products", "AI Chat", "Other products"],
  },
  errors: {
    columns: ["Error", "Service", "Severity", "Occurrences", "Last seen"],
    text: "Error events are unavailable until authorized observability services are connected.",
    filters: ["All severities", "Critical", "Warning", "Information"],
  },
  audit: {
    columns: ["Event", "Actor", "Scope", "Action", "Time"],
    text: "Privileged activity requires a verified audit log service. No audit events are simulated.",
    filters: ["All actions", "Identity", "Membership", "Configuration"],
  },
  support: {
    columns: ["Ticket", "Organization", "Priority", "Status", "Updated"],
    text: "Support tickets require verified platform access and a connected support service.",
    filters: ["All statuses", "Open", "In progress", "Resolved"],
  },
};
export function AdminPage({ title, pagePath }: { title: string; pagePath: string }) {
  const [mobile, setMobile] = useState(false);
  useEffect(() => {
    if (!mobile) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobile(false);
    };
    document.addEventListener("keydown", close);
    return () => {
      document.body.style.overflow = previous;
      document.removeEventListener("keydown", close);
    };
  }, [mobile]);
  const slug = pagePath.split("/")[2] || "overview";
  const detail = pagePath.split("/").length > 3;
  const sidebar = (
    <aside className={`admin-sidebar ${mobile ? "admin-sidebar-open" : ""}`}>
      <Link to="/" aria-label="OraOne home">
        <Brand />
      </Link>
      <span className="admin-label">PLATFORM ADMINISTRATION</span>
      <div className="admin-environment">
        <LockKeyhole />
        <div>
          Restricted preview<small>Access not verified</small>
        </div>
      </div>
      <nav aria-label="Platform administration">
        {sections.map((s, i) => (
          <div key={s.path}>
            {(i === 0 || sections[i - 1]?.group !== s.group) && <h3>{s.group}</h3>}
            <Link
              to={s.path}
              className={
                (s.path === "/admin" ? pagePath === s.path : pagePath.startsWith(s.path))
                  ? "admin-nav-current"
                  : ""
              }
              onClick={() => setMobile(false)}
            >
              <s.icon />
              {s.name}
            </Link>
          </div>
        ))}
      </nav>
      <Button asChild variant="topbar">
        <Link to="/app">
          Customer workspace
          <ArrowUpRight />
        </Link>
      </Button>
    </aside>
  );
  return (
    <div className="phase-admin">
      {sidebar}
      <Dialog open={mobile} onOpenChange={setMobile}>
        <DialogContent className="translate-x-0 translate-y-0 mobile-navigation-dialog admin-navigation-dialog">
          <DialogTitle>Platform administration</DialogTitle>
          <DialogDescription className="sr-only">
            Administration destinations. Verified access is required for private operations.
          </DialogDescription>
          {sidebar}
        </DialogContent>
      </Dialog>
      <div className="admin-main">
        <header>
          <div>
            <Button
              variant="ghost"
              size="icon"
              className="admin-mobile-toggle"
              aria-label={
                mobile ? "Close administration navigation" : "Open administration navigation"
              }
              aria-expanded={mobile}
              onClick={() => setMobile(!mobile)}
            >
              {mobile ? <X /> : <Menu />}
            </Button>
            <span>Platform administration</span>
            <ChevronRight />
            <strong>{title}</strong>
          </div>
          <span className="admin-access-state">
            <LockKeyhole />
            Unverified access
          </span>
        </header>
        <main>
          <nav className="marketing-breadcrumb" aria-label="Breadcrumb">
            <Link to="/admin">Platform</Link>
            <span>/</span>
            <span>{title}</span>
          </nav>
          <div className="admin-page-heading">
            <div>
              <h1>{title}</h1>
              <p>
                {detail
                  ? "Membership, access and activity details remain private until authorization is verified."
                  : slug === "overview"
                    ? "An operations view across identity, organizations, products and platform health."
                    : `Review ${title.toLowerCase()} across the OraOne platform.`}
              </p>
            </div>
            <Button disabled variant="outline">
              <SlidersHorizontal />
              Manage unavailable
            </Button>
          </div>
          <div className="admin-access-notice">
            <ShieldCheck />
            <div>
              <strong>Authorized platform access required</strong>
              <p>
                Private records and management tools stay locked until your account and platform
                role are verified.
              </p>
            </div>
            <Button asChild variant="outline">
              <Link to="/auth/sign-in">
                Sign in
                <ArrowRight />
              </Link>
            </Button>
          </div>
          {["billing", "subscriptions"].includes(slug) ? (
            <section className="admin-section">
              <h2>Free access for everyone</h2>
              <p>
                No paid plans, invoices or payment collection are part of the current offering.
                Actual consumption requires authorized metering.
              </p>
              {tableDefinitions["usage"] && <AdminTable definition={tableDefinitions["usage"]} />}
            </section>
          ) : detail ? (
            <AdminDetails organization={slug === "organizations"} />
          ) : slug === "overview" ? (
            <AdminOverview />
          ) : slug === "products" ? (
            <AdminProducts />
          ) : tableDefinitions[slug] ? (
            <AdminTable definition={tableDefinitions[slug]} />
          ) : ["monitoring", "infrastructure", "ai-models"].includes(slug) ? (
            <AdminOperations slug={slug} />
          ) : slug === "security" ? (
            <AdminSecurity />
          ) : slug === "feature-flags" || slug === "entitlements" ? (
            <AdminControls entitlements={slug === "entitlements"} />
          ) : (
            <AdminSettings />
          )}
        </main>
        <footer>OraOne platform administration · Frontend preview · No privileged access</footer>
      </div>
    </div>
  );
}
function AdminOverview() {
  return (
    <>
      <div className="admin-metrics">
        {[
          { title: "Registered users", text: "Identity directory required", icon: Users },
          { title: "Organizations", text: "Organization service required", icon: Building2 },
          { title: "Free access", text: "No payments required", icon: CreditCard },
          { title: "AI usage", text: "Metering service required", icon: ChartNoAxesCombined },
        ].map((m) => (
          <article key={m.title}>
            <div>
              <span>{m.title}</span>
              <m.icon />
            </div>
            <strong>—</strong>
            <p>{m.text}</p>
          </article>
        ))}
      </div>
      <section className="admin-section">
        <h2>Platform health</h2>
        <div className="admin-service-list">
          {[
            "Identity & access",
            "Workspace APIs",
            "AI model providers",
            "Knowledge ingestion",
            "Channel delivery",
          ].map((s) => (
            <div key={s}>
              <Network />
              <span>{s}</span>
              <span className="status-pill planned">Not monitored</span>
            </div>
          ))}
        </div>
      </section>
      <section className="admin-section">
        <h2>Attention & recent activity</h2>
        <div className="admin-summary-grid">
          {[
            {
              title: "Audit activity",
              path: "/admin/audit",
              text: "Verified event history unavailable",
            },
            {
              title: "Errors to investigate",
              path: "/admin/errors",
              text: "Error telemetry unavailable",
            },
            {
              title: "Support activity",
              path: "/admin/support",
              text: "Support service unavailable",
            },
          ].map((i) => (
            <Link to={i.path} key={i.path}>
              <h3>{i.title}</h3>
              <p>{i.text}</p>
              <ArrowUpRight />
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}
function AdminTable({
  definition,
}: {
  definition: { columns: string[]; text: string; filters: string[] };
}) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState(definition.filters[0] || "All");
  const [sort, setSort] = useState(definition.columns[0] || "");
  return (
    <section className="admin-section">
      <div className="admin-table-toolbar">
        <label className="admin-search">
          <Search />
          <input
            aria-label="Search records"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search records"
          />
        </label>
        <label className="admin-filter">
          <span>Status</span>
          <select
            aria-label="Filter records"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            {definition.filters.map((f) => (
              <option key={f}>{f}</option>
            ))}
          </select>
        </label>
        <Button disabled variant="outline">
          Export unavailable
        </Button>
      </div>
      <div className="admin-table-scroll" tabIndex={0} aria-label="Records table">
        <table>
          <thead>
            <tr>
              {definition.columns.map((c) => (
                <th key={c} aria-sort={sort === c ? "ascending" : "none"}>
                  <Button variant="ghost" onClick={() => setSort(c)}>
                    {c}
                    <ChevronDown />
                  </Button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody />
        </table>
        <div className="admin-empty">
          <LockKeyhole />
          <h3>
            {search || filter !== definition.filters[0]
              ? "No authorized records to filter"
              : "Records unavailable"}
          </h3>
          <p>{definition.text}</p>
          <span>No private data loaded</span>
        </div>
      </div>
      <div className="admin-pagination">
        <span>Records not loaded · Access required</span>
        <div>
          <Button variant="outline" size="icon" disabled aria-label="Previous page">
            <ChevronLeft />
          </Button>
          <Button variant="outline" size="icon" disabled aria-label="Next page">
            <ChevronRight />
          </Button>
        </div>
      </div>
    </section>
  );
}
function AdminProducts() {
  return (
    <section className="admin-section">
      <h2>Central product registry</h2>
      <p>
        Public portfolio labels only. Visibility, release management and entitlement changes require
        authorized services.
      </p>
      <div className="admin-table-scroll" tabIndex={0} aria-label="Product registry">
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>Portfolio status</th>
              <th>Workspace visibility</th>
              <th>Management</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.slug}>
                <td>
                  <strong>{p.name}</strong>
                  <small>{p.capabilities.join(" · ")}</small>
                </td>
                <td>
                  <span className={`status-pill ${p.slug === "chat" ? "" : "planned"}`}>
                    {p.status}
                  </span>
                </td>
                <td>Service verification required</td>
                <td>
                  <Button disabled variant="outline" size="sm">
                    Configure
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
function AdminOperations({ slug }: { slug: string }) {
  const services =
    slug === "ai-models"
      ? [
          "Model provider configuration",
          "Provider authorization",
          "Model routing",
          "Evaluation results",
        ]
      : slug === "infrastructure"
        ? ["API services", "Knowledge queues", "Storage services", "Background jobs"]
        : ["API request volume", "Response latency", "Provider failures", "Queue health"];
  return (
    <>
      <div className="admin-metrics">
        {services.map((s) => (
          <article key={s}>
            <div>
              <span>{s}</span>
              <Activity />
            </div>
            <strong>—</strong>
            <p>Authorized telemetry unavailable</p>
          </article>
        ))}
      </div>
      <section className="admin-section">
        <h2>{slug === "ai-models" ? "Provider configuration" : "Service observability"}</h2>
        <div className="admin-service-list">
          {services.map((s) => (
            <div key={s}>
              <Network />
              <span>{s}</span>
              <span className="status-pill planned">Not connected</span>
            </div>
          ))}
        </div>
      </section>
      <section className="admin-section">
        <h2>{slug === "ai-models" ? "Evaluation history" : "Incident timeline"}</h2>
        <div className="admin-telemetry-empty">
          <ChartNoAxesCombined />
          <p>
            No verified telemetry available. Metrics and charts appear only after the monitoring
            service is connected.
          </p>
        </div>
      </section>
    </>
  );
}
function AdminSecurity() {
  return (
    <>
      <section className="admin-section">
        <h2>Separate authorization scopes</h2>
        <div className="admin-scope-grid">
          <div>
            <ShieldCheck />
            <h3>Platform roles</h3>
            <p>Internal platform operations</p>
            <ul>
              {["super_admin", "admin", "manager", "user"].map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
          <div>
            <Users />
            <h3>Organization roles</h3>
            <p>Workspace membership and collaboration</p>
            <ul>
              {["admin", "admin", "member", "viewer"].map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        </div>
        <p>
          Role assignments are not loaded or editable here. Platform authorization remains
          authoritative in the existing PostgreSQL service, mapped through the verified account
          identity.
        </p>
      </section>
      <AdminTable
        definition={{
          columns: ["Security event", "Actor", "Scope", "Result", "Time"],
          text: "Verified security and privileged-access history is not connected.",
          filters: ["All events", "Privileged access", "Role changes", "Session events"],
        }}
      />
    </>
  );
}
function AdminControls({ entitlements }: { entitlements: boolean }) {
  return (
    <section className="admin-section">
      <h2>{entitlements ? "Workspace product entitlements" : "Product feature configuration"}</h2>
      <p>
        {entitlements
          ? "Entitlements must be read and enforced by authorized services, never inferred from a public product status."
          : "Flag values require an authoritative configuration service. No preview toggle can change production behavior."}
      </p>
      <div className="admin-table-scroll" tabIndex={0} aria-label="Product controls">
        <table>
          <thead>
            <tr>
              <th>Product</th>
              <th>{entitlements ? "Workspace scope" : "Configuration"}</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.slug}>
                <td>{p.name}</td>
                <td>Not loaded</td>
                <td>Access required</td>
                <td>
                  <Button variant="outline" size="sm" disabled>
                    {entitlements ? "Manage access" : "Edit flags"}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
function AdminDetails({ organization }: { organization: boolean }) {
  return (
    <>
      <section className="admin-section">
        <h2>{organization ? "Organization information" : "Account information"}</h2>
        <div className="admin-details-grid">
          {(organization
            ? ["Organization", "Workspaces", "Access", "Active products"]
            : ["Identity", "Platform role", "Account status", "Organization memberships"]
          ).map((s) => (
            <div key={s}>
              <span>{s}</span>
              <strong>Private · Not loaded</strong>
            </div>
          ))}
        </div>
        <Button disabled variant="outline">
          Sensitive actions unavailable
        </Button>
      </section>
      <AdminTable
        definition={{
          columns: ["Activity", "Actor", "Scope", "Time"],
          text: "Details and activity require authorized access to this record. No personal or organizational data is exposed.",
          filters: ["All activity", "Membership", "Access", "Configuration"],
        }}
      />
    </>
  );
}
function AdminSettings() {
  return (
    <section className="admin-section">
      <h2>Platform configuration</h2>
      <p>
        Settings are read-only unavailable states until an authorized configuration service is
        connected.
      </p>
      <div className="admin-settings-grid">
        {[
          "Identity configuration",
          "Workspace defaults",
          "Model routing",
          "Notifications",
          "Security policy",
          "Environment settings",
        ].map((s) => (
          <div key={s}>
            <Settings />
            <div>
              <h3>{s}</h3>
              <p>Current values not loaded</p>
            </div>
            <Button variant="outline" disabled size="sm">
              Edit
            </Button>
          </div>
        ))}
      </div>
    </section>
  );
}
