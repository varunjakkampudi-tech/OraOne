import { lazy, memo, Suspense, useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  MessageSquare,
  Bot,
  UserRoundCheck,
  CalendarCheck,
  CheckCircle2,
  Circle,
  Users,
  Download,
  SlidersHorizontal,
  ChevronDown,
  ArrowRight,
  ArrowUpRight,
  CheckCheck,
  MoreHorizontal,
  BookOpen,
  ShieldCheck,
  Activity,
} from "lucide-react";
const PerformanceChart = lazy(() => import("./performance-chart"));
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/lib/workspace-context";
import { products } from "@/lib/oraone";
import { ChartSkeleton } from "./loading";
import { StatusBadge } from "./status-badge";

const chartData = [
  { day: "Oct 6", conversations: 1250, resolved: 900 },
  { day: "Oct 7", conversations: 1680, resolved: 1220 },
  { day: "Oct 8", conversations: 1390, resolved: 1090 },
  { day: "Oct 9", conversations: 1930, resolved: 1420 },
  { day: "Oct 10", conversations: 1740, resolved: 1360 },
  { day: "Oct 11", conversations: 2210, resolved: 1620 },
  { day: "Oct 12", conversations: 2286, resolved: 2188 },
];
const CHART_TABS = ["Conversation volume", "Answered by AI", "Response time"] as const;
type ChartTab = (typeof CHART_TABS)[number];

// Sample values only. No trend or percentage change is shown because there is no real comparison.
const metrics = [
  {
    label: "Total conversations",
    value: "12,486",
    note: "Website and AI Chat conversations",
    icon: MessageSquare,
    theme: "blue",
    link: "/app/inbox",
    cta: "Inbox",
    points: "0,24 14,22 28,17 42,20 56,13 70,16 88,9",
  },
  {
    label: "Answered without a person",
    value: "78.4%",
    note: "Answered by an assistant with no handoff",
    icon: Bot,
    theme: "cyan",
    link: "/app/products/chat/assistants",
    cta: "AI Assistants",
    points: "0,25 14,21 28,23 42,15 56,17 70,9 88,5",
  },
  {
    label: "Qualified leads",
    value: "326",
    note: "2.6% conversion rate · 48 sent to your CRM",
    icon: UserRoundCheck,
    theme: "amber",
    link: "/app/leads",
    cta: "CRM Leads",
    points: "0,24 14,26 28,17 42,20 56,11 70,14 88,5",
  },
  {
    label: "Appointments booked",
    value: "94",
    note: "82% via AI Chat website assistants",
    icon: CalendarCheck,
    theme: "violet",
    link: "/app/activity",
    cta: "Activity",
    points: "0,27 14,22 28,25 42,18 56,19 70,9 88,3",
  },
] as const;

export const Dashboard = memo(function Dashboard() {
  const { workspace, sample } = useWorkspace();
  const [setup, setSetup] = useState(true);
  const [acknowledged, setAcknowledged] = useState(false);
  const [days, setDays] = useState("Last 7 Days");
  const [chartTab, setChartTab] = useState<ChartTab>("Conversation volume");
  const [channel, setChannel] = useState("All Channels & Products");
  const performanceData = useMemo(
    () =>
      chartData.map((d) => ({
        ...d,
        conversations:
          chartTab === "Answered by AI"
            ? 78 + (d.conversations % 8)
            : chartTab === "Response time"
              ? 1.2 + (d.conversations % 5) / 10
              : d.conversations,
        resolved:
          chartTab === "Answered by AI"
            ? 70 + (d.resolved % 8)
            : chartTab === "Response time"
              ? 0.8 + (d.resolved % 4) / 10
              : d.resolved,
      })),
    [chartTab],
  );
  function exportReport() {
    const contents = sample
      ? "OraOne sample report — illustrative data only\nMetric,Value\nConversations,12486\nAI resolution,78.4%\nQualified leads,326\nAppointments,94\n"
      : "OraOne report\nNo connected workspace data\n";
    const url = URL.createObjectURL(new Blob([contents], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "oraone-sample-report.csv";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <div className="page-content dashboard-content">
      <div className="page-heading dashboard-heading">
        <div>
          <h1>
            Good morning, Alex <span className="greeting-dot" />
          </h1>
          <p>
            {sample
              ? `A sample overview of ${workspace}.`
              : `Overview for ${workspace}. No services are connected yet.`}
          </p>
        </div>
        <div className="page-actions">
          <label className="select-control">
            <span className="sr-only">Date range</span>
            <select aria-label="Date range" value={days} onChange={(e) => setDays(e.target.value)}>
              <option>Last 7 Days</option>
              <option>Last 14 Days</option>
              <option>Last 30 Days</option>
            </select>
            <ChevronDown />
          </label>
          <label className="select-control channel-select">
            <select
              aria-label="Channel filter"
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
            >
              <option>All Channels & Products</option>
              <option>AI Chat · Website</option>
            </select>
            <SlidersHorizontal />
          </label>
          <Button variant="outline" size="sm" onClick={exportReport}>
            <Download />
            Export report
          </Button>
        </div>
      </div>
      {sample ? (
        <div className="service-notice dashboard-notice" role="note">
          <ShieldCheck />
          <span>You are viewing a sample workspace. Changes are not saved.</span>
        </div>
      ) : (
        <div className="service-notice dashboard-notice" role="note">
          <ShieldCheck />
          <span>No services are connected to this workspace, so no figures are shown.</span>
        </div>
      )}
      {setup && sample && (
        <section className="setup-panel">
          <div className="setup-heading">
            <div className="setup-title">
              <span className="setup-icon">
                <CheckCircle2 />
              </span>
              <h2>Finish your workspace setup</h2>
              <span className="completion-tag">Sample: 3 of 5 steps done</span>
            </div>
            <Button
              variant="link"
              size="sm"
              className="dismiss-button"
              onClick={() => setSetup(false)}
            >
              Dismiss
            </Button>
          </div>
          <p>Finish essential configuration to get your AI Chat workspace ready.</p>
          <div className="setup-progress">
            <span />
          </div>
          <div className="setup-steps">
            <div className="setup-step completed">
              <CheckCircle2 />
              <div>
                <strong>Create first AI assistant</strong>
                <small>Completed in sample workspace</small>
              </div>
            </div>
            <div className="setup-step completed">
              <CheckCircle2 />
              <div>
                <strong>Add knowledge source</strong>
                <small>142 sample sources</small>
              </div>
            </div>
            <div className="setup-step completed">
              <CheckCircle2 />
              <div>
                <strong>Connect website</strong>
                <small>Sample website connected</small>
              </div>
            </div>
            <Link
              to="/app/products/chat/assistants/$id/playground"
              params={{ id: "support" }}
              className="setup-step next"
            >
              <Circle />
              <div>
                <strong>Test your assistant</strong>
                <small>
                  Open playground <ArrowRight />
                </small>
              </div>
            </Link>
            <Link to="/app/team/invitations" className="setup-step">
              <Users />
              <div>
                <strong>Invite teammates</strong>
                <small>
                  Open invitations <ArrowRight />
                </small>
              </div>
            </Link>
          </div>
        </section>
      )}
      <div className="section-eyebrow">
        <span>WORKSPACE PERFORMANCE</span>
        <span className="sample-label">
          {sample
            ? "Illustrative totals · Not summed from loaded sample records"
            : "No live workspace data connected"}{" "}
          · {days}
        </span>
      </div>
      <section className="metric-grid">
        {metrics.map((m, i) => (
          <article className={`metric-card metric-${m.theme}`} key={m.label}>
            <div className="metric-top">
              <h3>{m.label}</h3>
              <m.icon />
            </div>
            {sample ? (
              <span className="status-pill is-demo sample-badge">Sample data</span>
            ) : (
              <span className="status-pill is-planned sample-badge">Unavailable</span>
            )}
            <div className="metric-value">
              {sample
                ? days === "Last 7 Days"
                  ? m.value
                  : i === 1
                    ? "78.4%"
                    : (
                        Number(m.value.replace(",", "")) * (days === "Last 14 Days" ? 2 : 4)
                      ).toLocaleString()
                : "—"}
            </div>
            <p>{sample ? m.note : "No connected data yet"}</p>
            <div className="metric-bottom">
              {!sample ? (
                <span className="metric-footnote">Not measured</span>
              ) : i === 0 ? (
                <svg
                  className="mini-chart"
                  viewBox="0 0 90 34"
                  role="img"
                  aria-label="Sample conversation trend"
                >
                  <polyline points={m.points} />
                </svg>
              ) : (
                <span className="metric-footnote">
                  {i === 1 ? (
                    <>
                      <span className="resolution-ring" />
                      9,788 answered by AI
                    </>
                  ) : i === 2 ? (
                    <>
                      <span className="status-dot" />
                      HubSpot sample
                    </>
                  ) : (
                    <>Website & AI Chat</>
                  )}
                </span>
              )}
              <Link to={m.link}>
                {m.cta}
                <ArrowRight />
              </Link>
            </div>
          </article>
        ))}
      </section>
      {!acknowledged && sample && (
        <section className="attention-panel">
          <div className="attention-heading">
            <div className="attention-title">
              <span className="attention-symbol">✳</span>
              <div>
                <h2>
                  Needs your attention <span className="attention-badge">4 sample items</span>
                </h2>
                <p>Sample items that may need a closer look.</p>
              </div>
            </div>
            <Button
              variant="link"
              size="sm"
              className="acknowledge"
              onClick={() => setAcknowledged(true)}
            >
              Mark all as reviewed <CheckCheck />
            </Button>
          </div>
          <div className="attention-grid">
            <article className="attention-card danger">
              <div className="flag-label">
                <span className="status-dot" />
                Waiting for a person<small>Urgent</small>
              </div>
              <h3>8 conversations awaiting a teammate</h3>
              <p>Website conversations ready for human follow-up.</p>
              <Link to="/app/inbox">
                Open Inbox (8)
                <ArrowRight />
              </Link>
            </article>
            <article className="attention-card warning">
              <div className="flag-label">
                <span className="status-dot" />
                Knowledge to review<small>Pending</small>
              </div>
              <h3>3 sources need your review</h3>
              <p>Keep your assistant’s answers accurate and up to date.</p>
              <Link to="/app/products/chat/knowledge">
                Review Sources
                <ArrowRight />
              </Link>
            </article>
            <article className="attention-card info">
              <div className="flag-label">
                <span className="status-dot" />
                Strong leads<small>Score 85+</small>
              </div>
              <h3>12 leads requiring follow-up</h3>
              <p>Enterprise inquiries ready for your sales team.</p>
              <Link to="/app/leads">
                Review Leads
                <ArrowRight />
              </Link>
            </article>
            <article className="attention-card neutral">
              <div className="flag-label">
                <span className="status-dot" />
                Connection check<small>Check needed</small>
              </div>
              <h3>1 connection needs attention</h3>
              <p>Review the sample CRM connection configuration.</p>
              <Link to="/app/integrations/connected">
                View Connections
                <ArrowRight />
              </Link>
            </article>
          </div>
        </section>
      )}
      <section className="chart-panel">
        <div className="panel-heading">
          <div>
            <h2>Conversations and answers over time</h2>
            <p>Sample daily totals for conversations and AI answers.</p>
          </div>
          <div className="segmented-control">
            {CHART_TABS.map((tab) => (
              <Button
                key={tab}
                variant="ghost"
                size="sm"
                className={tab === chartTab ? "segment-active" : ""}
                onClick={() => setChartTab(tab)}
              >
                {tab}
              </Button>
            ))}
          </div>
        </div>
        <div className="chart-legend">
          <span>
            <i className="legend-blue" />
            Total conversations <strong>{sample ? "12,486" : "—"}</strong>
          </span>
          <span>
            <i className="legend-cyan" />
            Answered by AI <strong>{sample ? "9,788 (78.4%)" : "—"}</strong>
          </span>
          <span className="live-caption">
            <span className="status-dot" />
            Sample data · {channel === "AI Chat · Website" ? "Website" : "All channels"}
          </span>
        </div>
        <div className="performance-chart">
          {sample ? (
            <Suspense fallback={<ChartSkeleton />}>
              <PerformanceChart data={performanceData} />
            </Suspense>
          ) : (
            <div className="empty-state">
              <Activity />
              <h3>No conversations yet</h3>
              <p>Add the website chat widget to start receiving customer messages.</p>
              <Button asChild variant="outline" size="sm">
                <Link to="/app/products/chat/assistants/$id/widget" params={{ id: "support" }}>
                  Set up the widget
                  <ArrowRight />
                </Link>
              </Button>
            </div>
          )}
        </div>
      </section>
      <div className="dashboard-lower">
        {sample ? (
          <>
            <section>
              <div className="panel-heading">
                <div>
                  <h2>Your AI assistants</h2>
                  <p>Sample assistants and the knowledge they use.</p>
                </div>
                <Button variant="link" asChild size="sm">
                  <Link to="/app/products/chat/assistants">
                    View all
                    <ArrowRight />
                  </Link>
                </Button>
              </div>
              <div className="assistant-summary">
                <span className="assistant-icon">
                  <Bot />
                </span>
                <div>
                  <h3>Customer Support</h3>
                  <p>Website assistant · 142 sample sources</p>
                </div>
                <span className="status-pill is-demo">Sample</span>
                <Button asChild variant="ghost" size="icon" title="Open support assistant">
                  <Link to="/app/products/chat/assistants/$id" params={{ id: "support" }}>
                    <ArrowUpRight />
                  </Link>
                </Button>
              </div>
              <div className="assistant-summary">
                <span className="assistant-icon cyan-icon">
                  <UserRoundCheck />
                </span>
                <div>
                  <h3>Sales Assistant</h3>
                  <p>Lead qualification · 28 sample sources</p>
                </div>
                <span className="status-pill is-demo">Sample</span>
                <Button asChild variant="ghost" size="icon" title="Open sales assistant">
                  <Link to="/app/products/chat/assistants/$id" params={{ id: "sales" }}>
                    <ArrowUpRight />
                  </Link>
                </Button>
              </div>
            </section>
            <section>
              <div className="panel-heading">
                <div>
                  <h2>Workspace activity</h2>
                  <p>A snapshot of your sample workspace.</p>
                </div>
                <Button asChild variant="ghost" size="icon" title="All activity">
                  <Link to="/app/activity">
                    <MoreHorizontal />
                  </Link>
                </Button>
              </div>
              <div className="activity-row">
                <span className="activity-icon">
                  <BookOpen />
                </span>
                <div>
                  <strong>Knowledge sources reviewed</strong>
                  <p>Customer Support · Sample event</p>
                </div>
                <small>12m ago</small>
              </div>
              <div className="activity-row">
                <span className="activity-icon">
                  <Users />
                </span>
                <div>
                  <strong>New leads captured</strong>
                  <p>Website assistant · Sample event</p>
                </div>
                <small>34m ago</small>
              </div>
            </section>
          </>
        ) : (
          <div className="empty-state">
            <h3>No assistants or activity yet</h3>
            <p>Create an assistant to see its activity here.</p>
            <Button asChild variant="outline" size="sm">
              <Link to="/app/products/chat/assistants/new">
                Create an assistant
                <ArrowRight />
              </Link>
            </Button>
          </div>
        )}
      </div>
      <section className="product-directory-section">
        <div className="panel-heading">
          <div>
            <h2>Products</h2>
            <p>Your OraOne products, all in one place.</p>
          </div>
          <Button asChild variant="link" size="sm">
            <Link to="/app/products">
              Explore products
              <ArrowRight />
            </Link>
          </Button>
        </div>
        <div className="compact-products">
          {products.map((p, i) => (
            <div key={p.slug}>
              <span className="product-number">{String(i + 1).padStart(2, "0")}</span>
              <strong>{p.name}</strong>
              <StatusBadge status={p.slug === "chat" ? "available" : "planned"} />
            </div>
          ))}
        </div>
      </section>
      <footer className="page-footer">
        <span>© 2026 OraOne · Sample workspace</span>
        <div>
          <Link to="/docs">Documentation</Link>
          <Link to="/help">
            Help & Support
            <ArrowUpRight />
          </Link>
        </div>
      </footer>
    </div>
  );
});
