import { useEffect, useState, type ReactNode } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import {
  Bot,
  Search,
  Plus,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCircle2,
  Circle,
  MessageSquare,
  Globe,
  FileText,
  MoreHorizontal,
  Download,
  Upload,
  Mail,
  Users,
  Settings,
  ChevronRight,
  ShieldCheck,
  Plug,
  LockKeyhole,
  BookOpen,
  CreditCard,
  Copy,
  Eye,
  EyeOff,
  Code2,
  ExternalLink,
  Inbox,
  Filter,
  Send,
  ChevronDown,
  Headphones,
  Phone,
  Workflow,
  Lightbulb,
  Boxes,
  Smartphone,
  Building2,
  Network,
  Activity,
  Clock,
  X,
  SlidersHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { WorkspaceShell, Brand } from "./shell";
import { useWorkspace } from "@/lib/workspace-context";
import { Dashboard } from "./dashboard";
import {
  demoAssistants,
  visibleConversationId,
  demoCustomers,
  demoConversations,
  products,
} from "@/lib/oraone";
import manifest from "@/lib/route-manifest.json";

const productIcons = [
  MessageSquare,
  Phone,
  MessageSquare,
  Inbox,
  Workflow,
  Lightbulb,
  Boxes,
  Smartphone,
  Building2,
  Network,
];
type PageProps = { title: string; pagePath: string };
function Notice({ children }: { children?: ReactNode }) {
  return (
    <div className="service-notice">
      <ShieldCheck />
      <span>
        {children ||
          "Sample workspace. Live services are not connected; changes here are preview-only."}
      </span>
    </div>
  );
}
function Empty({
  title = "No records yet",
  text = "Connect your workspace to see real data here.",
}: {
  title?: string;
  text?: string;
}) {
  return (
    <div className="empty-state">
      <Inbox />
      <h3>{title}</h3>
      <p>{text}</p>
      <Button asChild variant="outline" size="sm">
        <Link to="/docs/getting-started">
          Read setup guide
          <ArrowRight />
        </Link>
      </Button>
    </div>
  );
}
function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <>
      <div className="breadcrumb">
        WORKSPACE <span>/</span>
        <strong>{title.toUpperCase()}</strong>
      </div>
      <div className="page-heading">
        <div>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        <div className="page-actions">{action}</div>
      </div>
    </>
  );
}
function SectionNavigation({ pagePath }: { pagePath: string }) {
  const actual = useRouterState({ select: (s) => s.location.pathname });
  const id = actual.split("/")[5] || "support";
  let prefix = "/app";
  if (pagePath.startsWith("/app/products/chat/assistants/") && !pagePath.endsWith("/new"))
    prefix = "/app/products/chat/assistants/$id";
  else if (pagePath.startsWith("/app/products/chat/knowledge"))
    prefix = "/app/products/chat/knowledge";
  else if (pagePath.startsWith("/app/products/"))
    prefix = "/app/products/" + pagePath.split("/")[3];
  else if (
    [
      "/app/settings",
      "/app/account",
      "/app/team",
      "/app/billing",
      "/app/integrations",
      "/app/analytics",
    ].some((p) => pagePath.startsWith(p))
  )
    prefix = "/app/" + pagePath.split("/")[2];
  else return null;
  const children = manifest.filter(
    (r) =>
      r.path.startsWith(prefix + "/") &&
      !r.path.slice(prefix.length + 1).includes("/") &&
      !r.path.slice(prefix.length + 1).startsWith("$") &&
      r.path !== prefix + "/overview",
  );
  return (
    <nav className="page-tabs" aria-label="Section navigation">
      <Link
        to={prefix.includes("$id") ? "/app/products/chat/assistants/$id" : prefix}
        {...(prefix.includes("$id") ? { params: { id } } : {})}
        className={pagePath === prefix ? "tab-active" : ""}
        activeOptions={{ exact: true }}
      >
        Overview
      </Link>
      {children.map((r) => (
        <Link
          to={r.path}
          {...(r.path.includes("$id") ? { params: { id } } : {})}
          key={r.path}
          className={pagePath === r.path ? "tab-active" : ""}
          activeOptions={{ exact: true }}
        >
          {r.title}
        </Link>
      ))}
    </nav>
  );
}
// Manifest paths are validated file routes. Runtime links use the generated registry.
export function WorkspacePage(props: PageProps) {
  return <WorkspaceContent {...props} />;
}
function WorkspaceContent({ title, pagePath }: PageProps) {
  // Hooks run before any early return so their order is stable across routes.
  const { sample } = useWorkspace();
  if (pagePath === "/app/workspaces/new")
    return (
      <div className="page-content">
        <PageHeader
          title="Create workspace"
          description="Create a saved workspace in your account."
        />
        <Notice>
          This sample workspace cannot save new workspaces. Use your account to create one.
        </Notice>
        <Button asChild>
          <Link to="/studio">
            Create workspace in your account
            <ArrowRight />
          </Link>
        </Button>
      </div>
    );
  if (pagePath === "/app") return <Dashboard />;
  const slug = pagePath.split("/")[3];
  const product = products.find((p) => p.slug === slug);
  if (product && product.slug !== "chat")
    return <PlannedProduct product={product} pagePath={pagePath} title={title} />;
  if (
    !sample &&
    !pagePath.startsWith("/app/settings") &&
    !pagePath.startsWith("/app/account") &&
    pagePath !== "/app/products"
  )
    return (
      <div className="page-content">
        <PageHeader title={title} description={descriptionFor(pagePath)} />
        <Empty
          title="Your workspace is ready"
          text="This workspace has no connected services or records. Acme sample data is not shown here."
        />
      </div>
    );
  const inbox = pagePath.startsWith("/app/inbox") || pagePath.endsWith("/conversations");
  return (
    <div className={`page-content ${inbox ? "inbox-page" : ""}`}>
      <PageHeader
        title={title}
        description={descriptionFor(pagePath)}
        action={<PageAction pagePath={pagePath} />}
      />
      <SectionNavigation pagePath={pagePath} />
      {pagePath === "/app/products" ? (
        <ProductDirectory />
      ) : inbox ? (
        <ConversationInbox pagePath={pagePath} />
      ) : pagePath.startsWith("/app/customers") || pagePath.startsWith("/app/leads") ? (
        <CustomersPage pagePath={pagePath} />
      ) : pagePath === "/app/products/chat/assistants/new" ? (
        <AssistantCreate />
      ) : pagePath.startsWith("/app/products/chat/assistants/") ? (
        <AssistantDetail pagePath={pagePath} />
      ) : pagePath.endsWith("/assistants") ? (
        <Assistants />
      ) : pagePath.includes("/knowledge") ? (
        <Knowledge pagePath={pagePath} />
      ) : pagePath.includes("/analytics") ? (
        <AnalyticsPage />
      ) : pagePath.startsWith("/app/integrations") ? (
        <Integrations pagePath={pagePath} />
      ) : pagePath.startsWith("/app/team") ? (
        <TeamPage pagePath={pagePath} />
      ) : pagePath.startsWith("/app/billing") || pagePath === "/app/settings/billing" ? (
        <Billing pagePath={pagePath} />
      ) : pagePath.includes("/settings") ||
        pagePath.includes("/account") ||
        pagePath.includes("/workspaces") ? (
        <SettingsPage pagePath={pagePath} />
      ) : pagePath === "/app/products/chat" ? (
        <ChatOverview />
      ) : pagePath === "/app/search" ? (
        <SearchPage />
      ) : pagePath.endsWith("/templates") ? (
        <Templates />
      ) : pagePath === "/app/notifications" || pagePath === "/app/activity" ? (
        <ActivityPage />
      ) : (
        <>
          <Notice />
          <Empty
            title={sample ? "Ready when your workspace is" : "Start building your workspace"}
            text="This page is ready for a connected service. No live records are available."
          />
        </>
      )}
    </div>
  );
}
function descriptionFor(path: string) {
  if (path.includes("/assistants"))
    return "Create, configure and manage your AI website assistants.";
  if (path.includes("/knowledge")) return "The knowledge behind accurate, helpful answers.";
  if (path.includes("/inbox") || path.includes("/conversations"))
    return "Every customer conversation. One connected inbox.";
  if (path.includes("/customers") || path.includes("/leads"))
    return "A complete view of the people connecting with your business.";
  if (path.includes("/analytics"))
    return "Understand your conversations, customers and assistant performance.";
  if (path.includes("/integrations"))
    return "Connect your workspace to the tools your business relies on.";
  if (path.includes("/team")) return "The people and permissions behind your workspace.";
  if (path.includes("/billing")) return "Free access and workspace consumption in one place.";
  if (path.includes("/settings") || path.includes("/account"))
    return "Manage your preferences and workspace configuration.";
  return "Your business, connected through OraOne.";
}
function PageAction({ pagePath }: { pagePath: string }) {
  if (pagePath.endsWith("/assistants") || pagePath === "/app/products/chat")
    return (
      <Button asChild>
        <Link to="/app/products/chat/assistants/new">
          <Plus />
          Create assistant
        </Link>
      </Button>
    );
  if (pagePath === "/app/products/chat/knowledge")
    return (
      <Button asChild>
        <Link to="/app/products/chat/knowledge/documents">
          <Plus />
          Add knowledge
        </Link>
      </Button>
    );
  if (pagePath.startsWith("/app/team"))
    return (
      <Button asChild variant="outline">
        <Link to="/app/team/invitations">
          <Plus />
          Invite teammate
        </Link>
      </Button>
    );
  return null;
}
function ProductDirectory() {
  return (
    <>
      <Notice>
        Product availability is separate from live service readiness. AI Chat is the current
        portfolio product.
      </Notice>
      <div className="product-grid">
        {products.map((p, i) => {
          const Icon = productIcons[i] || Boxes;
          return (
            <article className="product-card" key={p.slug}>
              <div className="product-card-top">
                <span className={`product-icon product-icon-${i % 4}`}>
                  <Icon />
                </span>
                <span className={`status-pill ${i ? "planned" : ""}`}>{p.status}</span>
              </div>
              <h2>{p.name}</h2>
              <p>{p.description}</p>
              <div className="capability-tags">
                {p.capabilities.slice(0, 2).map((c) => (
                  <span key={c}>{c}</span>
                ))}
              </div>
              <Button asChild variant={i ? "outline" : "default"}>
                <Link to={"/app/products/" + p.slug}>
                  {i ? "Explore preview" : "Open AI Chat"}
                  <ArrowRight />
                </Link>
              </Button>
            </article>
          );
        })}
      </div>
    </>
  );
}
function PlannedProduct({
  product,
  pagePath,
  title,
}: {
  product: (typeof products)[number];
  pagePath: string;
  title: string;
}) {
  const index = products.findIndex((p) => p.slug === product.slug);
  const Icon = productIcons[index] || Boxes;
  return (
    <div className="page-content">
      <PageHeader
        title={product.name}
        description={product.description}
        action={<span className="status-pill planned">{product.status} · Not released</span>}
      />
      <SectionNavigation pagePath={pagePath} />
      <div className="vision-banner">
        <span className="vision-icon">
          <Icon />
        </span>
        <span className="eyebrow">THE ORAONE ECOSYSTEM</span>
        <h2>A connected future for {product.short.toLowerCase()}.</h2>
        <p>
          {pagePath.split("/").length > 4
            ? `${title} is part of the planned ${product.short} experience. `
            : ""}
          This product is not released. These are intended capabilities, not currently available
          features.
        </p>
        <Button variant="outline" asChild>
          <Link to="/roadmap">
            View product roadmap
            <ArrowRight />
          </Link>
        </Button>
      </div>
      <h2 className="section-title">Planned capabilities</h2>
      <div className="feature-grid">
        {product.capabilities.map((c, i) => (
          <article className="feature-item" key={c}>
            <span className="feature-number">0{i + 1}</span>
            <h3>{c}</h3>
            <p>
              Designed to work within one shared OraOne identity, workspace and permission system.
            </p>
            <span className="status-pill planned">Not yet available</span>
          </article>
        ))}
      </div>
      <Notice>
        Release dates and access details have not been announced. No signup or waitlist service is
        connected.
      </Notice>
      <div className="related-band">
        <BookOpen />
        <div>
          <h3>Part of one unified platform</h3>
          <p>Explore the full ten-product OraOne ecosystem.</p>
        </div>
        <Button asChild variant="outline">
          <Link to="/app/products">
            All products
            <ArrowRight />
          </Link>
        </Button>
      </div>
    </div>
  );
}

function Assistants() {
  const { sample } = useWorkspace();
  return (
    <>
      <Notice />
      <div className="toolbar">
        <label className="search-field">
          <Search />
          <input
            placeholder="Search assistants"
            onChange={(e) =>
              document.querySelectorAll<HTMLElement>(".assistant-card").forEach((el) => {
                el.hidden = !el.innerText.toLowerCase().includes(e.target.value.toLowerCase());
              })
            }
          />
        </label>
        <Button variant="outline">
          <Filter />
          All assistants
        </Button>
      </div>
      {sample ? (
        <div className="assistant-grid">
          {[
            {
              id: "support",
              name: "Customer Support",
              text: "Helpful answers, grounded in your business knowledge.",
              sources: 142,
              icon: Headphones,
            },
            {
              id: "sales",
              name: "Sales Assistant",
              text: "Turn website interest into qualified conversations.",
              sources: 28,
              icon: Users,
            },
            {
              id: "onboarding",
              name: "Onboarding Guide",
              text: "A welcoming first step for every new customer.",
              sources: 36,
              icon: BookOpen,
            },
          ].map((a) => (
            <article className="assistant-card" key={a.id}>
              <div className="product-card-top">
                <span className="assistant-icon">
                  <a.icon />
                </span>
                <span className="status-pill">Sample assistant</span>
              </div>
              <h2>{a.name}</h2>
              <p>{a.text}</p>
              <div className="assistant-stats">
                <span>
                  <BookOpen />
                  {a.sources} sources
                </span>
                <span>
                  <Globe />
                  Website
                </span>
              </div>
              <div className="assistant-card-actions">
                <Button asChild variant="outline">
                  <Link to="/app/products/chat/assistants/$id" params={{ id: a.id }}>
                    Manage assistant
                    <ArrowRight />
                  </Link>
                </Button>
                <Button asChild variant="ghost" size="icon" title="Configure assistant">
                  <Link to="/app/products/chat/assistants/$id/editor" params={{ id: a.id }}>
                    <Settings />
                  </Link>
                </Button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty title="Create your first assistant" />
      )}
    </>
  );
}
function AssistantCreate() {
  const [name, setName] = useState("");
  const [template, setTemplate] = useState("Customer support");
  const [review, setReview] = useState(false);
  return (
    <div className="form-layout">
      <form
        className="settings-form"
        onSubmit={(e) => {
          e.preventDefault();
          setReview(true);
        }}
      >
        <Notice>
          This is an assistant configuration preview. Saving and deployment need a connected
          workspace service.
        </Notice>
        <h2>Give your assistant a purpose</h2>
        <p className="muted-copy">Start with a name and the job you want it to do.</p>
        <label>
          Assistant name
          <input
            required
            placeholder="e.g. Customer Support"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label>
          Description
          <textarea placeholder="What should this assistant help customers with?" rows={3} />
        </label>
        <label>
          Use case
          <select value={template} onChange={(e) => setTemplate(e.target.value)}>
            <option>Customer support</option>
            <option>Lead qualification</option>
            <option>Customer onboarding</option>
          </select>
        </label>
        <label>
          Language
          <select>
            <option>English</option>
            <option>Hindi</option>
            <option>Spanish</option>
          </select>
        </label>
        <div className="form-actions">
          <Button asChild variant="outline">
            <Link to="/app/products/chat/assistants">Cancel</Link>
          </Button>
          <Button type="submit">
            Review configuration
            <ArrowRight />
          </Button>
        </div>
        {review && (
          <div className="review-notice">
            <CheckCircle2 />
            <p>
              <strong>{name}</strong> is ready to configure for {template.toLowerCase()}. This
              preview has not created or deployed an assistant.
            </p>
          </div>
        )}
      </form>
      <aside className="context-aside">
        <Bot />
        <h3>A great assistant starts with a clear purpose.</h3>
        <p>
          Keep its role focused, connect reliable knowledge and review answers before deployment.
        </p>
        <Link to="/docs/ai-chat">
          Assistant setup guide
          <ArrowUpRight />
        </Link>
      </aside>
    </div>
  );
}
function AssistantDetail({ pagePath }: { pagePath: string }) {
  const actual = useRouterState({ select: (s) => s.location.pathname });
  const id = actual.split("/")[5] || "support";
  const name = demoAssistants.find((a) => a.id === id)?.name ?? "Assistant not found";
  const [instructions, setInstructions] = useState(
    "You are a helpful customer support assistant. Answer clearly and accurately using the connected knowledge base. If you do not know the answer, offer to connect the customer with a teammate.",
  );
  useEffect(() => {
    setInstructions(
      id === "sales"
        ? "Qualify sales inquiries, understand customer needs and offer a sales teammate. Never invent prices."
        : id === "onboarding"
          ? "Guide customers through onboarding with approved setup documentation."
          : "Answer support questions clearly using approved knowledge; offer a teammate when unsure.",
    );
  }, [id]);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);
  const [widgetColor, setWidgetColor] = useState("blue");
  const [draft, setDraft] = useState("Hi! How can we help you today?");
  const last = pagePath.split("/").at(-1);
  if (last === "playground")
    return (
      <>
        <Notice>
          Live assistant testing requires a model connection. No generated responses are simulated
          here.
        </Notice>
        <div className="playground-layout">
          <div className="playground-chat">
            <div className="widget-head">
              <Bot />
              <div>
                <strong>{name}</strong>
                <small>Assistant playground</small>
              </div>
              <span className="status-pill planned">Not connected</span>
            </div>
            <div className="playground-empty">
              <Bot />
              <h2>Test the knowledge behind your assistant.</h2>
              <p>Model calls are unavailable until your workspace is connected.</p>
              <div className="suggestion-grid">
                <span>What services do you offer?</span>
                <span>How can I contact your team?</span>
              </div>
            </div>
            <div className="disabled-composer">
              <input disabled placeholder="Connect a model to test your assistant" />
              <Button disabled size="icon" aria-label="Send test message">
                <Send />
              </Button>
            </div>
          </div>
          <aside className="context-aside">
            <h3>Test configuration</h3>
            <dl>
              <dt>Assistant</dt>
              <dd>{name}</dd>
              <dt>Knowledge</dt>
              <dd>{id === "sales" ? 28 : id === "onboarding" ? 12 : 142} sample sources</dd>
              <dt>Model</dt>
              <dd>Not connected</dd>
            </dl>
            <Button asChild variant="outline">
              <Link to="/app/products/chat/assistants/$id/behavior" params={{ id }}>
                Configure behavior
                <Settings />
              </Link>
            </Button>
          </aside>
        </div>
      </>
    );
  if (last === "install")
    return (
      <>
        <Notice>
          Installation is a design preview. A deployment ID and verified endpoint are required
          before this snippet can run.
        </Notice>
        <div className="settings-form">
          <h2>Add OraOne to your website</h2>
          <p className="muted-copy">
            Your embed code will be generated after publishing your assistant.
          </p>
          <pre className="code-panel">
            {"<!-- OraOne widget installation -->\n<!-- A published assistant ID is required. -->"}
          </pre>
          <Button variant="outline" disabled>
            <Copy />
            Installation code unavailable
          </Button>
          <h3 className="section-title">Installation checklist</h3>
          {[
            "Publish your assistant",
            "Add the generated script before the closing body tag",
            "Verify your website domain",
            "Test your assistant on the website",
          ].map((t, i) => (
            <div className="checklist-row" key={t}>
              <span>{i + 1}</span>
              {t}
            </div>
          ))}
        </div>
      </>
    );
  if (last === "widget")
    return (
      <>
        <Notice />
        <div className="widget-editor">
          <div className="settings-form">
            <h2>Make it feel like your brand</h2>
            <label>
              Display name
              <input key={id} defaultValue={name} />
            </label>
            <label>
              Welcome message
              <textarea
                aria-label="Welcome message"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={3}
              />
            </label>
            <div className="field-label">Brand color</div>
            <div className="swatches">
              {["blue", "cyan", "green", "ink"].map((c) => (
                <Button
                  key={c}
                  className={`swatch swatch-${c}`}
                  size="icon"
                  variant="ghost"
                  aria-label={`${c} widget color`}
                  onClick={() => setWidgetColor(c)}
                >
                  {widgetColor === c && <Check />}
                </Button>
              ))}
            </div>
            <label>
              Widget position
              <select>
                <option>Bottom right</option>
                <option>Bottom left</option>
              </select>
            </label>
            <Button onClick={() => setSaved(true)}>Apply to preview</Button>
            {saved && <p className="muted-copy">Applied to this preview only.</p>}
          </div>
          <div className={`widget-preview widget-${widgetColor}`}>
            <div className="widget-head">
              <Bot />
              <div>
                <strong>{name}</strong>
                <small>OraOne website assistant</small>
              </div>
              <X />
            </div>
            <div className="widget-body">
              <span className="widget-message">{draft}</span>
              <span className="widget-time">Just now</span>
            </div>
            <div className="disabled-composer">
              <input placeholder="Your message..." disabled />
              <Send />
            </div>
            <div className="widget-powered">Powered by OraOne · Preview</div>
          </div>
        </div>
      </>
    );
  if (last === "knowledge") return <Knowledge pagePath={pagePath} />;
  if (last === "analytics" || last === "quality") return <AnalyticsPage />;
  if (last === "versions")
    return (
      <>
        <Notice />
        <div className="data-table">
          <div className="table-header">
            <span>Version</span>
            <span>Changes</span>
            <span>Status</span>
            <span>Created</span>
          </div>
          <div className="table-row">
            <strong>Draft version</strong>
            <span>Sample assistant configuration</span>
            <span className="status-pill planned">Not published</span>
            <span>Sample record</span>
          </div>
        </div>
      </>
    );
  return (
    <div className="form-layout">
      <div className="settings-form">
        <Notice />
        <div className="assistant-detail-title">
          <span className="assistant-icon">
            <Headphones />
          </span>
          <div>
            <h2>{name}</h2>
            <p>Website assistant · Sample configuration</p>
          </div>
        </div>
        <label>
          Assistant name
          <input key={id} defaultValue={name} />
        </label>
        <label>
          Instructions
          <textarea
            rows={7}
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
          />
        </label>
        <label>
          Response tone
          <select>
            <option>Professional & friendly</option>
            <option>Concise & direct</option>
            <option>Warm & conversational</option>
          </select>
        </label>
        <label>
          Knowledge behavior
          <select>
            <option>Use connected knowledge only</option>
            <option>Ask clarifying questions</option>
          </select>
        </label>
        <label className="checkbox-field">
          <input type="checkbox" defaultChecked />
          Offer human handoff when an answer is unavailable
        </label>
        <div className="form-actions">
          <Button
            variant="outline"
            onClick={() => {
              setInstructions("");
              setSaved(false);
            }}
          >
            Clear draft
          </Button>
          <Button onClick={() => setSaved(true)}>
            Apply to preview
            <Check />
          </Button>
        </div>
        {saved && (
          <p className="review-notice">
            Configuration updated in this preview. Nothing has been saved to a live service.
          </p>
        )}
      </div>
      <aside className="context-aside">
        <h3>Assistant configuration</h3>
        <dl>
          <dt>Channel</dt>
          <dd>Website</dd>
          <dt>Portfolio</dt>
          <dd>AI Chat · Current product</dd>
          <dt>Deployment</dt>
          <dd>Not connected</dd>
        </dl>
        <Button asChild variant="outline">
          <Link to="/app/products/chat/assistants/$id/playground" params={{ id }}>
            Open playground
            <ArrowUpRight />
          </Link>
        </Button>
        <Link to="/app/products/chat/assistants/$id/install" params={{ id }}>
          Installation guide
          <ArrowRight />
        </Link>
      </aside>
    </div>
  );
}
function Knowledge({ pagePath }: { pagePath: string }) {
  const [query, setQuery] = useState("");
  const [source, setSource] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [dialog, setDialog] = useState(false);
  const rows = [
    {
      name: "Acme Help Center",
      type: "Website",
      url: "help.example.com",
      size: "84 pages",
      status: "Sample source",
    },
    {
      name: "Product documentation",
      type: "Website",
      url: "docs.example.com",
      size: "58 pages",
      status: "Sample source",
    },
    {
      name: "Customer support handbook.pdf",
      type: "Document",
      url: "PDF document",
      size: "2.4 MB",
      status: "Sample source",
    },
    {
      name: "Product FAQs.pdf",
      type: "Document",
      url: "PDF document",
      size: "840 KB",
      status: "Needs review",
    },
  ];
  return (
    <>
      <Notice />
      <div className="knowledge-stats">
        <div>
          <BookOpen />
          <strong>142</strong>
          <span>Sample sources</span>
        </div>
        <div>
          <FileText />
          <strong>2</strong>
          <span>Sample documents</span>
        </div>
        <div>
          <Globe />
          <strong>2</strong>
          <span>Sample websites</span>
        </div>
      </div>
      <div className="toolbar">
        <label className="search-field">
          <Search />
          <input
            placeholder="Search knowledge sources"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <Button variant="outline" onClick={() => setDialog(true)}>
          <Plus />
          Add source
        </Button>
      </div>
      <div className="data-table knowledge-table">
        <div className="table-header">
          <span>Source name</span>
          <span>Type</span>
          <span>Content</span>
          <span>Status</span>
        </div>
        {rows
          .filter(
            (r) =>
              r.name.toLowerCase().includes(query.toLowerCase()) &&
              (!pagePath.endsWith("/websites") || r.type === "Website") &&
              (!pagePath.endsWith("/documents") || r.type === "Document"),
          )
          .map((r) => (
            <div className="table-row" key={r.name}>
              <span className="source-name">
                {r.type === "Website" ? <Globe /> : <FileText />}
                <span>
                  <strong>{r.name}</strong>
                  <small>{r.url}</small>
                </span>
              </span>
              <span>{r.type}</span>
              <span>{r.size}</span>
              <span className={`status-pill ${r.status === "Needs review" ? "planned" : ""}`}>
                {r.status}
              </span>
            </div>
          ))}
      </div>
      {selected.length > 0 && (
        <div className="review-notice">
          Selected for preview: {selected.join(", ")}. Files have not been uploaded or ingested.
        </div>
      )}
      <Dialog open={dialog} onOpenChange={setDialog}>
        <DialogContent>
          <DialogTitle>Add knowledge source</DialogTitle>
          <DialogDescription>
            Choose a file or review a website address. Ingestion requires a connected service.
          </DialogDescription>
          <div className="settings-form compact-form">
            <label>
              Website address
              <input
                type="url"
                placeholder="https://your-website.com"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              />
            </label>
            <label className="upload-zone">
              <Upload />
              <strong>Choose documents</strong>
              <span>PDF, TXT or Markdown</span>
              <input
                type="file"
                multiple
                accept=".pdf,.txt,.md"
                onChange={(e) => setSelected(Array.from(e.target.files || []).map((f) => f.name))}
              />
            </label>
            <Button
              variant="outline"
              onClick={() => {
                if (source) setSelected([...selected, source]);
                setDialog(false);
              }}
            >
              Review selection
              <ArrowRight />
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
function ConversationInbox({ pagePath }: { pagePath: string }) {
  const { sample } = useWorkspace();
  const route = useRouterState({ select: (s) => s.location.pathname });
  const initial = demoConversations.find((c) => route.endsWith("/" + c.id)) || demoConversations[0];
  const [selected, setCurrent] = useState(initial);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All conversations");
  const [reply, setReply] = useState("");
  const [drafts, setDrafts] = useState<string[]>([]);
  const matches = demoConversations.filter(
    (c) =>
      (filter === "All conversations" || c.status === filter) &&
      (c.name + " " + c.preview).toLowerCase().includes(query.toLowerCase()),
  );
  const current = matches.find((c) => c.id === visibleConversationId(selected?.id, filter, query));
  useEffect(() => {
    setDrafts([]);
    setReply("");
  }, [current?.id]);
  if (!sample) return <Empty title="Your inbox is ready" />;
  return (
    <>
      <div className="inbox-toolbar">
        <div className="segmented-control">
          {["All conversations", "Open", "Resolved"].map((f) => (
            <Button
              variant="ghost"
              className={filter === f ? "segment-active" : ""}
              key={f}
              onClick={() => setFilter(f)}
            >
              {f}
              {f === "All conversations" && <span className="small-count">5</span>}
            </Button>
          ))}
        </div>
        <span className="sample-label">
          {
            demoConversations.filter(
              (c) =>
                (filter === "All conversations" || c.status === filter) &&
                (c.name + " " + c.preview).toLowerCase().includes(query.toLowerCase()),
            ).length
          }{" "}
          shown · {demoConversations.length} loaded samples · 12,486 illustrative aggregate, not
          linked records
        </span>
      </div>
      <div className="inbox-layout">
        <div className="conversation-list">
          <label className="search-field">
            <Search />
            <input
              placeholder="Search conversations"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          {demoConversations
            .filter(
              (c) =>
                (filter === "All conversations" || c.status === filter) &&
                (c.name + " " + c.preview).toLowerCase().includes(query.toLowerCase()),
            )
            .map((c) => (
              <Button
                variant="ghost"
                key={c.id}
                className={`conversation-row ${current?.id === c.id ? "conversation-selected" : ""}`}
                onClick={() => {
                  setCurrent(c);
                  setDrafts([]);
                  setReply("");
                }}
              >
                <span className="avatar">{c.initials}</span>
                <span className="conversation-row-body">
                  <span>
                    <strong>{c.name}</strong>
                    <small>{c.time}</small>
                  </span>
                  <span className="conversation-preview">{c.preview}</span>
                  <span>
                    <span className={`status-pill ${c.status === "Resolved" ? "" : "planned"}`}>
                      {c.status}
                    </span>
                    <small>
                      <Globe />
                      Website
                    </small>
                  </span>
                </span>
                {c.unread && <span className="unread-dot" />}
              </Button>
            ))}
        </div>
        {current ? (
          <>
            <div className="conversation-detail">
              <div className="conversation-header">
                <span className="avatar">{current.initials}</span>
                <div>
                  <h2>{current.name}</h2>
                  <p>
                    <Globe />
                    Website · Customer Support
                  </p>
                </div>
                <span className="status-pill planned">Sample transcript</span>
              </div>
              <div className="transcript">
                <div className="transcript-date">TODAY · SAMPLE CONVERSATION</div>
                <div className="customer-message">
                  Hi, I’m looking for some information about your services.<small>10:40 AM</small>
                </div>
                <div className="assistant-message">
                  <span className="message-agent">
                    <Bot />
                    Customer Support
                  </span>
                  Hi {current.name.split(" ")[0]}! I’d be happy to help. What would you like to
                  know?
                  <small>10:40 AM · AI assistant</small>
                </div>
                <div className="customer-message">
                  {current.preview}
                  <small>10:42 AM</small>
                </div>
                <div className="handoff-note">
                  <Users />
                  This sample conversation is ready for a teammate.
                </div>
                {drafts.map((d, i) => (
                  <div className="assistant-message" key={i}>
                    <span className="message-agent">Alex · Draft preview</span>
                    {d}
                    <small>Not sent to a customer</small>
                  </div>
                ))}
              </div>
              <form
                className="reply-composer"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (reply.trim()) {
                    setDrafts([...drafts, reply]);
                    setReply("");
                  }
                }}
              >
                <div className="composer-label">
                  Reply draft <span>Not connected to a live channel</span>
                </div>
                <textarea
                  aria-label="Reply draft"
                  placeholder="Write a reply draft..."
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  rows={3}
                />
                <div>
                  <span className="sample-label">Preview only · No message will be sent</span>
                  <Button type="submit" size="sm" disabled={!reply.trim()}>
                    Preview draft
                    <ArrowRight />
                  </Button>
                </div>
              </form>
            </div>
            <aside className="customer-sidebar">
              <h3>Customer details</h3>
              <span className="avatar large-avatar">{current.initials}</span>
              <h2>{current.name}</h2>
              <p>{current.name.toLowerCase().split(" ")[0]}@example.com</p>
              <dl>
                <dt>Channel</dt>
                <dd>Website</dd>
                <dt>Location</dt>
                <dd>Sample profile</dd>
                <dt>Assistant</dt>
                <dd>Customer Support</dd>
                <dt>Status</dt>
                <dd>{current.status}</dd>
              </dl>
              <Button asChild variant="outline" size="sm">
                <Link to="/app/customers/$customerId" params={{ customerId: current.id }}>
                  View customer
                  <ArrowUpRight />
                </Link>
              </Button>
              <h3 className="section-title">Tags</h3>
              <span className="status-pill planned">Website inquiry</span>
            </aside>
          </>
        ) : (
          <Empty
            title="No matching conversations"
            text="Try another filter or search. No conversation is selected."
          />
        )}
      </div>
    </>
  );
}
function CustomersPage({ pagePath }: { pagePath: string }) {
  const { sample } = useWorkspace();
  const actual = useRouterState({ select: (s) => s.location.pathname });
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All statuses");
  const records = pagePath.startsWith("/app/leads")
    ? demoCustomers.filter((c) => c.status !== "Customer")
    : demoCustomers;
  const detail = pagePath.includes("$");
  const customer = demoCustomers.find((c) => actual.endsWith("/" + c.id)) || demoCustomers[0];
  if (!sample || !customer) return <Empty title="No customers yet" />;
  if (detail)
    return (
      <>
        <Notice />
        <div className="customer-profile">
          <span className="avatar large-avatar">{customer.initials}</span>
          <div>
            <h2>{customer.name}</h2>
            <p>{customer.email}</p>
          </div>
          <span className="status-pill">{customer.status}</span>
        </div>
        <div className="form-layout">
          <section className="detail-section">
            <h2>Customer overview</h2>
            <dl className="detail-list">
              <dt>Company</dt>
              <dd>{customer.company}</dd>
              <dt>Email</dt>
              <dd>{customer.email}</dd>
              <dt>Source</dt>
              <dd>{customer.channel}</dd>
              <dt>Last active</dt>
              <dd>{customer.date}</dd>
            </dl>
            <h2 className="section-title">Conversation history</h2>
            <Button asChild variant="outline">
              <Link to="/app/inbox/$conversationId" params={{ conversationId: customer.id }}>
                View sample conversation
                <ArrowRight />
              </Link>
            </Button>
          </section>
          <aside className="context-aside">
            <h3>Customer notes</h3>
            <textarea placeholder="Write a local draft note..." rows={5} />
            <p>Notes are preview-only and are not saved.</p>
          </aside>
        </div>
      </>
    );
  return (
    <>
      <Notice />
      <div className="toolbar">
        <label className="search-field">
          <Search />
          <input
            placeholder="Search name, email or company"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <label className="select-control">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            aria-label="Customer status"
          >
            <option>All statuses</option>
            <option>Customer</option>
            <option>Qualified</option>
            <option>New lead</option>
          </select>
          <ChevronDown />
        </label>
      </div>
      <div className="data-table customer-table">
        <div className="table-header">
          <span>Name</span>
          <span>Company</span>
          <span>Status</span>
          <span>Source</span>
          <span>Last active</span>
        </div>
        {records
          .filter(
            (c) =>
              (c.name + " " + c.email + " " + c.company)
                .toLowerCase()
                .includes(query.toLowerCase()) &&
              (status === "All statuses" || c.status === status),
          )
          .map((c) => (
            <Link
              to="/app/customers/$customerId"
              params={{ customerId: c.id }}
              className="table-row"
              key={c.id}
            >
              <span className="customer-name">
                <span className="avatar">{c.initials}</span>
                <span>
                  <strong>{c.name}</strong>
                  <small>{c.email}</small>
                </span>
              </span>
              <span>{c.company}</span>
              <span>
                <span className={`status-pill ${c.status === "New lead" ? "planned" : ""}`}>
                  {c.status}
                </span>
              </span>
              <span>
                <Globe className="inline-icon" />
                {c.channel}
              </span>
              <span>{c.date}</span>
            </Link>
          ))}
      </div>
      <div className="table-footer">
        <span>
          {
            records.filter(
              (c) =>
                (c.name + " " + c.email + " " + c.company)
                  .toLowerCase()
                  .includes(query.toLowerCase()) &&
                (status === "All statuses" || c.status === status),
            ).length
          }{" "}
          shown · {demoCustomers.length} loaded samples
        </span>
        <span>326 illustrative qualified leads · Not a linked record total</span>
      </div>
    </>
  );
}
function AnalyticsPage() {
  return (
    <>
      <Notice>
        These metrics are illustrative sample data, not measured production performance.
      </Notice>
      <div className="analytics-metrics">
        {[
          ["Conversations", "12,486", "Total sample volume"],
          ["AI resolution", "78.4%", "Sample autonomous resolutions"],
          ["Average response", "1.4s", "Illustrative response time"],
          ["Customer satisfaction", "4.8/5", "Sample rating"],
        ].map((m) => (
          <div key={m[0]}>
            <span>{m[0]}</span>
            <strong>{m[1]}</strong>
            <small>{m[2]}</small>
          </div>
        ))}
      </div>
      <div className="analytics-bars">
        <div className="panel-heading">
          <div>
            <h2>Conversations by day</h2>
            <p>Sample activity · October 6–12</p>
          </div>
          <span className="status-pill planned">Sample chart</span>
        </div>
        <div className="bar-chart">
          {[42, 65, 51, 78, 67, 90, 96].map((v, i) => (
            <div className={`bar-group bar-height-${i}`} key={i}>
              <div className="bar-pair">
                <i />
                <i />
              </div>
              <span>Oct {i + 6}</span>
            </div>
          ))}
        </div>
        <div className="chart-legend">
          <span>
            <i className="legend-blue" />
            Total conversations
          </span>
          <span>
            <i className="legend-cyan" />
            AI resolved
          </span>
        </div>
      </div>
      <div className="feature-grid">
        <section className="detail-section">
          <h2>Top conversation topics</h2>
          {["Product information", "Account support", "Getting started", "Pricing inquiries"].map(
            (t, i) => (
              <div className="topic-row" key={t}>
                <span>{t}</span>
                <strong>{[38, 27, 21, 14][i]}%</strong>
              </div>
            ),
          )}
        </section>
        <section className="detail-section">
          <h2>Quality & optimization</h2>
          <p className="muted-copy">
            Review your assistant’s knowledge coverage and behavior before connecting a live model.
          </p>
          <Button asChild variant="outline">
            <Link to="/app/products/chat/knowledge/coverage">
              Knowledge coverage
              <ArrowRight />
            </Link>
          </Button>
        </section>
      </div>
    </>
  );
}
function Integrations({ pagePath }: { pagePath: string }) {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState("");
  const [open, setOpen] = useState(false);
  const integrations = [
    {
      name: "HubSpot",
      initial: "H",
      type: "CRM",
      desc: "Bring customer and lead context into one workspace.",
    },
    {
      name: "Google Calendar",
      initial: "G",
      type: "Scheduling",
      desc: "Connect customer inquiries with appointment scheduling.",
    },
    {
      name: "Slack",
      initial: "#",
      type: "Team communication",
      desc: "Keep your team informed about important conversations.",
    },
    {
      name: "Notion",
      initial: "N",
      type: "Knowledge",
      desc: "Use your team’s documentation as assistant knowledge.",
    },
    {
      name: "Salesforce",
      initial: "S",
      type: "CRM",
      desc: "Coordinate customer records and sales workflows.",
    },
    {
      name: "Webhooks",
      initial: "↗",
      type: "Developer",
      desc: "Connect workspace events to your own business tools.",
    },
  ];
  return (
    <>
      <Notice>
        Integration connections are not configured. No external accounts have been connected.
      </Notice>
      <div className="toolbar">
        <label className="search-field">
          <Search />
          <input
            placeholder="Search integrations"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <span className="sample-label">0 live connections</span>
      </div>
      {pagePath.endsWith("/connected") ? (
        <Empty
          title="No integrations connected"
          text="Explore the catalog to see supported integration designs."
        />
      ) : (
        <div className="integration-grid">
          {integrations
            .filter((i) => i.name.toLowerCase().includes(query.toLowerCase()))
            .map((i, n) => (
              <article className="integration-card" key={i.name}>
                <div className="product-card-top">
                  <span className={`integration-logo integration-${n}`}>{i.initial}</span>
                  <span className="status-pill planned">Not connected</span>
                </div>
                <h2>{i.name}</h2>
                <span className="eyebrow">{i.type}</span>
                <p>{i.desc}</p>
                <Button
                  variant="outline"
                  onClick={() => {
                    setSelected(i.name);
                    setOpen(true);
                  }}
                >
                  View setup
                  <ArrowUpRight />
                </Button>
              </article>
            ))}
        </div>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogTitle>Connect {selected}</DialogTitle>
          <DialogDescription>
            Live {selected} connections require an authorized integration service. No credentials
            are collected in this preview.
          </DialogDescription>
          <div className="checklist-row">
            <span>1</span>Connect your workspace identity
          </div>
          <div className="checklist-row">
            <span>2</span>Authorize the integration provider
          </div>
          <div className="checklist-row">
            <span>3</span>Choose permitted data and events
          </div>
          <Button asChild variant="outline">
            <Link to="/docs">
              Integration documentation
              <ArrowRight />
            </Link>
          </Button>
        </DialogContent>
      </Dialog>
    </>
  );
}
function TeamPage({ pagePath }: { pagePath: string }) {
  const [email, setEmail] = useState("");
  const [review, setReview] = useState(false);
  if (pagePath.endsWith("/invitations"))
    return (
      <div className="settings-form">
        <Notice>
          Invitations require a connected identity service. No invitation emails will be sent.
        </Notice>
        <h2>Bring your team together</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setReview(true);
          }}
        >
          <label>
            Email address
            <input
              type="email"
              required
              placeholder="teammate@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label>
            Workspace role
            <select>
              <option>Member</option>
              <option>Viewer</option>
              <option>Admin</option>
            </select>
          </label>
          <Button type="submit" variant="outline">
            Review invitation
            <ArrowRight />
          </Button>
          {review && (
            <p className="review-notice">
              Invitation draft for {email}. This invitation has not been sent.
            </p>
          )}
        </form>
      </div>
    );
  if (pagePath.endsWith("/roles") || pagePath.endsWith("/permissions"))
    return (
      <>
        <Notice>
          Permissions displayed here are a design specification, not an active authorization system.
        </Notice>
        <div className="feature-grid">
          {["Owner", "Admin", "Member", "Viewer"].map((r, i) => (
            <section key={r} className="feature-item">
              <ShieldCheck />
              <h2>{r}</h2>
              <p>
                {
                  [
                    "Manages the organization and workspace access.",
                    "Manages workspace settings and team access.",
                    "Works with permitted assistants and customer data.",
                    "Reads explicitly authorized workspace information.",
                  ][i]
                }
              </p>
            </section>
          ))}
        </div>
      </>
    );
  return (
    <>
      <Notice />
      <div className="data-table team-table">
        <div className="table-header">
          <span>Team member</span>
          <span>Role</span>
          <span>Status</span>
          <span>Joined</span>
        </div>
        {[
          ["Alex Mercer", "AM", "Admin"],
          ["Sarah Wilson", "SW", "Admin"],
          ["James Chen", "JC", "Member"],
        ].map((m) => (
          <div className="table-row" key={m[0]}>
            <span className="customer-name">
              <span className="avatar">{m[1]}</span>
              <span>
                <strong>{m[0]}</strong>
                <small>Sample team member</small>
              </span>
            </span>
            <span>{m[2]}</span>
            <span className="status-pill planned">Sample</span>
            <span>Demo record</span>
          </div>
        ))}
      </div>
    </>
  );
}
function Billing({ pagePath }: { pagePath: string }) {
  return (
    <>
      <Notice>
        Access is free for everyone. No payment is required. Real consumption is unavailable until
        metering is connected.
      </Notice>
      <div className="billing-overview">
        <div>
          <span className="eyebrow">FREE ACCESS</span>
          <h2>Free for everyone</h2>
          <p>No paid plans, subscriptions or payment details are required.</p>
          <Button asChild variant="outline">
            <Link to="/pricing">
              View free access
              <ArrowRight />
            </Link>
          </Button>
        </div>
        <Users />
      </div>
      <section className="detail-section">
        <h2>Workspace usage</h2>
        <p className="muted-copy">Actual consumption has not been measured in this preview.</p>
        {["Conversations", "Knowledge storage", "AI model usage"].map((label) => (
          <div className="usage-line" key={label}>
            <span>{label}</span>
            <strong>Not connected</strong>
          </div>
        ))}
      </section>
      {(pagePath.endsWith("/invoices") || pagePath.endsWith("/payment-methods")) && (
        <Notice>
          Payments are not part of OraOne’s current offering. No payment information is collected.
        </Notice>
      )}
    </>
  );
}
function SettingsPage({ pagePath }: { pagePath: string }) {
  const { workspace } = useWorkspace();
  const [saved, setSaved] = useState(false);
  const [name, setName] = useState(pagePath.includes("/account") ? "Alex Mercer" : workspace);
  const security = pagePath.includes("/security");
  if (pagePath.endsWith("/api-keys"))
    return (
      <>
        <Notice>No API keys are generated or stored here.</Notice>
        <h2>Workspace API keys</h2>
        <p>Credentials require authorized issuance, workspace scopes and revocation.</p>
        <Button disabled>Generate key unavailable</Button>
      </>
    );
  if (pagePath === "/app/account/security")
    return (
      <>
        <Notice>This is a sample identity, not your signed-in account.</Notice>
        <h2>Personal account access</h2>
        <p>Email-code sign-in is also your recovery path; no password is used.</p>
        <Button asChild>
          <Link to="/auth/sign-in">Open email-code sign-in</Link>
        </Button>
      </>
    );
  return (
    <div className="form-layout">
      <form
        className="settings-form"
        onSubmit={(e) => {
          e.preventDefault();
          setSaved(true);
        }}
      >
        <Notice />
        <h2>
          {security
            ? "Security configuration"
            : pagePath.includes("/account")
              ? "Personal information"
              : "Workspace details"}
        </h2>
        <p className="muted-copy">Review the information and preferences for this workspace.</p>
        {security ? (
          <>
            <div className="security-setting">
              <ShieldCheck />
              <div>
                <h3>Multi-factor authentication</h3>
                <p>Requires a connected identity provider.</p>
              </div>
              <span className="status-pill planned">Not configured</span>
            </div>
            <div className="security-setting">
              <LockKeyhole />
              <div>
                <h3>API credentials</h3>
                <p>No keys have been generated in this preview.</p>
              </div>
            </div>
          </>
        ) : (
          <>
            <label>
              {pagePath.includes("/account") ? "Display name" : "Workspace name"}
              <input required value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label>
              {pagePath.includes("/account") ? "Email address" : "Workspace website"}
              <input
                type={pagePath.includes("/account") ? "email" : "url"}
                defaultValue={
                  pagePath.includes("/account") ? "alex@example.com" : "https://example.com"
                }
              />
            </label>
            <label>
              Timezone
              <select>
                <option>Asia / Kolkata (UTC +05:30)</option>
                <option>UTC</option>
                <option>America / New York</option>
              </select>
            </label>
            <label>
              Language
              <select>
                <option>English</option>
                <option>Hindi</option>
              </select>
            </label>
            <label className="checkbox-field">
              <input type="checkbox" defaultChecked />
              Include workspace activity in notification previews
            </label>
            <div className="form-actions">
              <Button
                variant="outline"
                type="button"
                onClick={() => {
                  setName(workspace);
                  setSaved(false);
                }}
              >
                Reset
              </Button>
              <Button type="submit">
                Apply to preview
                <Check />
              </Button>
            </div>
          </>
        )}
        {saved && (
          <p className="review-notice">
            Preferences updated for this preview only. They are not stored.
          </p>
        )}
      </form>
      <aside className="context-aside">
        <Settings />
        <h3>Your workspace, your way.</h3>
        <p>
          Workspace settings are shared by permitted team members. Personal settings apply only to
          your account.
        </p>
        <Link to="/app/account/preferences">
          Personal preferences
          <ArrowRight />
        </Link>
        <Link to="/docs/getting-started">
          Workspace documentation
          <ArrowUpRight />
        </Link>
      </aside>
    </div>
  );
}
function ChatOverview() {
  return (
    <>
      <Notice />
      <div className="chat-intro">
        <span className="assistant-icon">
          <Bot />
        </span>
        <div>
          <h2>Your knowledge. Your voice. Your AI assistants.</h2>
          <p>Build a consistent customer experience with knowledge-grounded website assistants.</p>
        </div>
        <span className="status-pill">Current product</span>
      </div>
      <Assistants />
      <div className="feature-grid section-spaced">
        {[
          [
            "Knowledge base",
            "Connect accurate information for your assistants.",
            "/app/products/chat/knowledge",
            BookOpen,
          ],
          [
            "Conversations",
            "Review customer messages and human handoffs.",
            "/app/products/chat/conversations",
            MessageSquare,
          ],
          [
            "Performance",
            "Understand quality and conversation trends.",
            "/app/products/chat/analytics",
            Activity,
          ],
        ].map(([title, description, to, Icon]) => (
          <section className="feature-item" key={String(title)}>
            <BookOpen />
            <h2>{String(title)}</h2>
            <p>{String(description)}</p>
            <Button variant="link" asChild>
              <Link to={String(to)}>
                Explore
                <ArrowRight />
              </Link>
            </Button>
          </section>
        ))}
      </div>
    </>
  );
}
function Templates() {
  return (
    <div className="feature-grid">
      {["Customer Support", "Sales Qualification", "Onboarding Guide", "Product Expert"].map(
        (name, i) => (
          <article className="feature-item" key={name}>
            <span className="assistant-icon">
              <Bot />
            </span>
            <h2>{name}</h2>
            <p>A focused starting point for a helpful, knowledge-grounded assistant.</p>
            <Button asChild variant="outline">
              <Link to="/app/products/chat/assistants/new">
                Configure assistant
                <ArrowRight />
              </Link>
            </Button>
          </article>
        ),
      )}
    </div>
  );
}
function SearchPage() {
  const [query, setQuery] = useState("");
  return (
    <>
      <label className="search-field full-search">
        <Search />
        <input
          placeholder="Search all workspace pages"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>
      <div className="search-results">
        {manifest
          .filter(
            (r) =>
              r.family === "workspace" &&
              !r.path.includes("$") &&
              r.title.toLowerCase().includes(query.toLowerCase()),
          )
          .slice(0, 25)
          .map((r) => (
            <Link className="search-result-row" to={r.path} key={r.path}>
              <Search />
              <div>
                <strong>{r.title}</strong>
                <small>{r.path}</small>
              </div>
              <ArrowUpRight />
            </Link>
          ))}
      </div>
    </>
  );
}
function ActivityPage() {
  return (
    <>
      <Notice />
      <div className="activity-feed">
        {[
          [
            "Knowledge sources reviewed",
            "Customer Support · 3 sample sources reviewed",
            "12 minutes ago",
          ],
          ["New leads captured", "Website assistant · Sample lead activity", "34 minutes ago"],
          ["Assistant configuration updated", "Alex Mercer · Sample configuration", "1 hour ago"],
          ["Workspace created", "Acme Corporation · Sample workspace event", "Yesterday"],
        ].map((r, i) => (
          <div className="activity-row" key={r[0]}>
            <span className="activity-icon">
              {i === 0 ? <BookOpen /> : i === 1 ? <Users /> : <Settings />}
            </span>
            <div>
              <h3>{r[0]}</h3>
              <p>{r[1]}</p>
            </div>
            <small>{r[2]}</small>
          </div>
        ))}
      </div>
    </>
  );
}

export { AuthPage } from "./auth";
export { OnboardingPage } from "./onboarding";
export { AdminPage } from "./admin";
