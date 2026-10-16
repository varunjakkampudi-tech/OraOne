import { useEffect, useState, type ReactNode } from "react";
import { Link } from "@tanstack/react-router";
import {
  ArrowRight,
  ArrowUpRight,
  Bot,
  BookOpen,
  Check,
  ChevronDown,
  Globe,
  Layers,
  LockKeyhole,
  Menu,
  MessageSquare,
  Network,
  Play,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  Workflow,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Brand } from "./shell";
import { products } from "@/lib/oraone";
import manifest from "@/lib/route-manifest.json";
import previewUrl from "@/assets/oraone-workspace-preview.png";
import teamPhoto from "@/assets/oraone-team.jpg";
import tourUrl from "@/assets/oraone-tour.mp4?url";
import tourWebm from "@/assets/oraone-tour.webm?url";
import { Dialog, DialogContent, DialogTitle, DialogDescription } from "@/components/ui/dialog";

type Props = { title: string; pagePath: string };
const productPath = (slug: string) =>
  `/products/${slug === "chat" ? "ai-chat" : slug === "voice" ? "ai-voice" : slug}`;
const solutions = [
  {
    slug: "customer-support",
    name: "Customer support",
    heading: "Give every question the right next step.",
    description:
      "Bring business knowledge and conversation context together, with a clear path to your team when a customer needs a person.",
    features: ["Knowledge-grounded answers", "A shared support inbox", "Human handoff"],
    icon: MessageSquare,
  },
  {
    slug: "lead-generation",
    name: "Lead generation",
    heading: "Turn customer interest into useful context.",
    description:
      "Design assistants that understand visitor intent and collect the information your team needs for a thoughtful follow-up.",
    features: ["Purposeful qualification", "Customer profiles", "Conversation history"],
    icon: Sparkles,
  },
  {
    slug: "sales",
    name: "Sales",
    heading: "Keep the conversation moving.",
    description:
      "Give your sales team a shared view of customer questions, needs and previous conversations, without losing the context between touchpoints.",
    features: ["Product knowledge", "Lead context", "Team collaboration"],
    icon: Users,
  },
  {
    slug: "small-business",
    name: "Small business",
    heading: "A connected starting point for your business.",
    description:
      "Start with a website assistant and one shared workspace. Shape the experience around the knowledge, people and customers you already have.",
    features: ["Website assistance", "Simple knowledge setup", "One workspace"],
    icon: Globe,
  },
] as const;
const resources = [
  { name: "Documentation", path: "/docs" },
  { name: "Help center", path: "/help" },
  { name: "Roadmap", path: "/roadmap" },
  { name: "Changelog", path: "/changelog" },
  { name: "Security", path: "/security" },
];

export function MarketingLayout({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return;
    const before = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", close);
    return () => {
      document.body.style.overflow = before;
      document.removeEventListener("keydown", close);
    };
  }, [open]);
  return (
    <div className="marketing-surface">
      <a className="skip-content" href="#main-content">
        Skip to content
      </a>
      <header className="marketing-header">
        <Link to="/" aria-label="OraOne home">
          <Brand />
        </Link>
        <nav aria-label="Main navigation" className="marketing-desktop-nav">
          <NavMenu
            title="Products"
            items={products.map((p) => ({
              name: p.name,
              path: productPath(p.slug),
              status: p.status,
            }))}
          />
          <NavMenu
            title="Solutions"
            items={solutions.map((s) => ({ name: s.name, path: `/solutions/${s.slug}` }))}
          />
          <Link to="/platform" activeProps={{ className: "nav-current" }}>
            Platform
          </Link>
          <Link to="/pricing" activeProps={{ className: "nav-current" }}>
            Pricing
          </Link>
          <NavMenu title="Resources" items={resources} />
        </nav>
        <div className="marketing-account">
          <Button asChild variant="ghost">
            <Link to="/auth/sign-in">Sign in</Link>
          </Button>
          <Button asChild>
            <Link to="/auth/sign-up">
              Get started
              <ArrowUpRight />
            </Link>
          </Button>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="marketing-menu-toggle"
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {open ? <X /> : <Menu />}
        </Button>
      </header>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="translate-x-0 translate-y-0 mobile-navigation-dialog">
          <DialogTitle>Explore OraOne</DialogTitle>
          <DialogDescription>Products, resources and account access.</DialogDescription>
          <nav
            className="marketing-mobile-nav"
            aria-label="Mobile navigation"
            onClick={(event) => {
              if ((event.target as HTMLElement).closest("a")) setOpen(false);
            }}
          >
            <Link to="/platform">Platform</Link>
            <Link to="/products">All products</Link>
            <Link to="/solutions">Solutions</Link>
            <Link to="/pricing">Pricing</Link>
            <Link to="/docs">Resources</Link>
            <Link to="/auth/sign-in">Sign in</Link>
            <Button asChild>
              <Link to="/auth/sign-up">
                Get started
                <ArrowRight />
              </Link>
            </Button>
          </nav>
        </DialogContent>
      </Dialog>
      <main id="main-content">{children}</main>
      <footer className="marketing-footer">
        <div className="marketing-footer-top">
          <div>
            <Brand />
            <p>
              One unified AI business platform.
              <br />
              Built around the conversations that matter.
            </p>
          </div>
          {[
            {
              title: "Platform",
              items: [
                { name: "Overview", path: "/platform" },
                { name: "All products", path: "/products" },
                { name: "AI Chat", path: "/products/ai-chat" },
                { name: "Integrations", path: "/integrations" },
                { name: "Pricing", path: "/pricing" },
              ],
            },
            {
              title: "Company",
              items: [
                { name: "About", path: "/about" },
                { name: "Contact", path: "/contact" },
                { name: "Request demo", path: "/demo" },
                { name: "Security", path: "/security" },
              ],
            },
            { title: "Resources", items: resources },
          ].map((group) => (
            <div key={group.title}>
              <h3>{group.title}</h3>
              {group.items.map((i) => (
                <Link key={i.path} to={i.path}>
                  {i.name}
                </Link>
              ))}
            </div>
          ))}
        </div>
        <div className="marketing-footer-bottom">
          <span>© 2026 OraOne</span>
          <div>
            {[
              { name: "Privacy", path: "/privacy" },
              { name: "Terms", path: "/terms" },
              { name: "Cookies", path: "/cookies" },
              { name: "Acceptable use", path: "/acceptable-use" },
              { name: "Refund policy", path: "/refund-policy" },
            ].map((i) => (
              <Link key={i.path} to={i.path}>
                {i.name}
              </Link>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
function NavMenu({
  title,
  items,
}: {
  title: string;
  items: { name: string; path: string; status?: string }[];
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost">
          {title}
          <ChevronDown />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="marketing-dropdown">
        {items.map((i) => (
          <DropdownMenuItem asChild key={i.path}>
            <Link to={i.path}>
              <span>{i.name}</span>
              {i.status && <small>{i.status}</small>}
            </Link>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
function Note({ children }: { children: ReactNode }) {
  return (
    <div className="marketing-note">
      <ShieldCheck aria-hidden="true" />
      <p>{children}</p>
    </div>
  );
}
function CTAs({ sample = false }: { sample?: boolean }) {
  return (
    <div className="marketing-ctas">
      <Button asChild>
        <Link to={sample ? "/app" : "/auth/sign-up"}>
          {sample ? "Explore sample workspace" : "Get started"}
          <ArrowUpRight />
        </Link>
      </Button>
      <Button asChild variant="outline">
        <Link to={sample ? "/demo" : "/platform"}>
          {sample ? "Request a demo" : "Explore platform"}
          <ArrowRight />
        </Link>
      </Button>
    </div>
  );
}
function Heading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="marketing-page-heading">
      <span className="marketing-eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  );
}
function Features({ items }: { items: { title: string; text: string; icon?: typeof Bot }[] }) {
  return (
    <div className="marketing-feature-grid">
      {items.map((i) => {
        const Icon = i.icon || Check;
        return (
          <article key={i.title}>
            <span className="marketing-feature-icon">
              <Icon />
            </span>
            <h3>{i.title}</h3>
            <p>{i.text}</p>
          </article>
        );
      })}
    </div>
  );
}
function InterfacePreview({ compact = false }: { compact?: boolean }) {
  return (
    <figure className={`marketing-interface ${compact ? "compact-preview" : ""}`}>
      <div className="interface-caption">
        <span>
          <span className="preview-dot" />
          OraOne workspace
        </span>
        <span>Sample data · Preview</span>
      </div>
      <Link to="/app" aria-label="Explore the sample OraOne dashboard">
        <img
          src={previewUrl}
          width={1280}
          height={850}
          alt="OraOne sample dashboard showing assistant setup, customer conversations, a shared inbox and conversation analytics"
          loading={compact ? "lazy" : "eager"}
          decoding="async"
        />
      </Link>
    </figure>
  );
}
function FAQ({ items }: { items: [string, string][] }) {
  return (
    <section className="marketing-section marketing-faq">
      <div>
        <span className="marketing-eyebrow">A LITTLE MORE CLARITY</span>
        <h2>Frequently asked questions</h2>
      </div>
      <Accordion type="single" collapsible>
        {items.map(([q, a], i) => (
          <AccordionItem value={String(i)} key={q}>
            <AccordionTrigger>{q}</AccordionTrigger>
            <AccordionContent>{a}</AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </section>
  );
}
function FinalCTA() {
  return (
    <section className="marketing-final">
      <span className="marketing-eyebrow">YOUR NEXT CONVERSATION STARTS HERE</span>
      <h2>Bring your workspace together.</h2>
      <p>Explore OraOne AI Chat and the vision for one connected platform.</p>
      <CTAs sample />
    </section>
  );
}
function ProductGrid() {
  return (
    <div className="marketing-product-grid">
      {products.map((p, i) => (
        <Link to={productPath(p.slug)} className="marketing-product" key={p.slug}>
          <div>
            <span className="product-index">{String(i + 1).padStart(2, "0")}</span>
            <span className={`status-pill ${p.slug === "chat" ? "" : "planned"}`}>{p.status}</span>
          </div>
          <h3>{p.name}</h3>
          <p>{p.description}</p>
          <span className="product-link">
            Explore {p.short}
            <ArrowUpRight />
          </span>
        </Link>
      ))}
    </div>
  );
}

function AppTour() {
  // The video is opt-in: nothing is requested until the visitor starts the tour,
  // so the home page can finish loading without downloading the media.
  const [tourStarted, setTourStarted] = useState(false);

  return (
    <section className="app-tour-section">
      <div className="app-tour-heading">
        <div>
          <span className="marketing-eyebrow">INSIDE ORAONE</span>
          <h2>Your workspace, in focus.</h2>
          <p>Take a closer look at the dashboard, inbox, customers and AI assistants.</p>
        </div>
        <Button asChild variant="outline">
          <Link to="/app">
            Open sample workspace
            <ArrowUpRight />
          </Link>
        </Button>
      </div>
      <figure>
        {tourStarted ? (
          <video
            className="app-tour-video"
            controls
            autoPlay
            muted
            playsInline
            preload="auto"
            poster={previewUrl}
            aria-label="OraOne sample workspace tour"
            aria-describedby="tour-description"
          >
            <source src={tourWebm} type="video/webm" />
            <source src={tourUrl} type="video/mp4" />
          </video>
        ) : (
          <button
            type="button"
            className="app-tour-start"
            onClick={() => setTourStarted(true)}
            aria-describedby="tour-description"
          >
            <img
              src={previewUrl}
              alt=""
              width={1280}
              height={900}
              loading="lazy"
              decoding="async"
            />
            <span className="app-tour-start-label">
              <Play aria-hidden="true" />
              Play the sample tour
            </span>
          </button>
        )}
        <figcaption id="tour-description">
          Silent visual tour: workspace overview, shared inbox, customer directory and assistant
          list. Sample data only.
        </figcaption>
      </figure>
    </section>
  );
}

export function MarketingHome() {
  return (
    <MarketingLayout>
      <section className="marketing-home-hero">
        <img
          className="marketing-hero-photo"
          src={previewUrl}
          width={1280}
          height={850}
          alt="OraOne dashboard with illustrative sample conversations and assistant analytics"
          fetchPriority="high"
          decoding="async"
        />
        <div className="marketing-hero-copy">
          <Link to="/products/ai-chat" className="marketing-announcement">
            <span className="preview-dot" />
            Meet OraOne AI Chat
            <ArrowRight />
          </Link>
          <h1>OraOne</h1>
          <h2>
            Customer conversations.
            <br />
            One connected workspace.
          </h2>
          <p>
            Your knowledge, AI assistants and team—together for more thoughtful customer
            experiences.
          </p>
          <div className="marketing-ctas">
            <Button asChild>
              <Link to="/app">
                Explore OraOne
                <ArrowUpRight />
              </Link>
            </Button>
            <Button asChild variant="secondary">
              <Link to="/demo">
                Request a demo
                <ArrowRight />
              </Link>
            </Button>
          </div>
          <span className="hero-footnote">Sample workspace · Live services not yet connected</span>
        </div>
      </section>
      <section className="marketing-capability-strip">
        {[
          { icon: Bot, name: "AI assistants" },
          { icon: MessageSquare, name: "Customer conversations" },
          { icon: BookOpen, name: "Business knowledge" },
          { icon: Users, name: "Connected teams" },
        ].map(({ icon: Icon, name }) => (
          <div key={name}>
            <Icon />
            <span>{name}</span>
          </div>
        ))}
      </section>
      <AppTour />
      <section className="marketing-section">
        <div className="marketing-section-heading">
          <span className="marketing-eyebrow">START WITH AI CHAT</span>
          <h2>Your knowledge. A more helpful conversation.</h2>
          <p>
            Give your website a business-aware assistant, then keep your team and customer context
            close.
          </p>
        </div>
        <Features
          items={[
            {
              title: "An assistant with a purpose",
              text: "Shape its role, tone and language around the questions your customers ask.",
              icon: Bot,
            },
            {
              title: "Grounded in your knowledge",
              text: "Prepare your documentation and website content as a trusted source for answers.",
              icon: BookOpen,
            },
            {
              title: "People stay in the loop",
              text: "Review conversations in a shared inbox and design a path to human support.",
              icon: MessageSquare,
            },
          ]}
        />
        <Button asChild variant="outline">
          <Link to="/products/ai-chat">
            Discover AI Chat
            <ArrowRight />
          </Link>
        </Button>
      </section>
      <section className="marketing-section section-tinted">
        <div className="marketing-section-heading">
          <span className="marketing-eyebrow">BUILT AROUND YOUR BUSINESS</span>
          <h2>Different needs. One shared foundation.</h2>
        </div>
        <div className="marketing-solution-grid">
          {solutions.slice(0, 3).map((s) => (
            <Link to={`/solutions/${s.slug}`} key={s.slug}>
              <s.icon />
              <h3>{s.name}</h3>
              <p>{s.description}</p>
              <ArrowUpRight />
            </Link>
          ))}
        </div>
      </section>
      <section className="marketing-section">
        <div className="marketing-section-heading">
          <span className="marketing-eyebrow">FROM KNOWLEDGE TO CONVERSATION</span>
          <h2>A thoughtful path to your first assistant.</h2>
        </div>
        <div className="marketing-steps">
          {[
            {
              title: "Create your workspace",
              text: "Bring your business identity and team into one place.",
            },
            {
              title: "Shape your assistant",
              text: "Define a purpose and prepare reliable knowledge.",
            },
            {
              title: "Review, then connect",
              text: "Test with a configured model before deploying to your website.",
            },
          ].map((s, i) => (
            <article key={s.title}>
              <span>0{i + 1}</span>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="marketing-section section-tinted">
        <div className="marketing-section-heading">
          <span className="marketing-eyebrow">THE ORAONE ECOSYSTEM</span>
          <h2>One account. Ten connected product visions.</h2>
          <p>
            Start with AI Chat. Explore the roadmap for voice, messaging, automation and beyond.
          </p>
        </div>
        <ProductGrid />
        <Note>
          AI Chat is the current product, not a claim of verified operational readiness. Other
          products are planned or a long-term vision.
        </Note>
      </section>
      <section className="marketing-section">
        <div className="marketing-two-columns">
          <div>
            <span className="marketing-eyebrow">CONNECTED, WITH CONTROL</span>
            <h2>A workspace built for shared context.</h2>
            <p>
              Customer conversations, knowledge and your team belong together. OraOne brings them
              into one consistent experience.
            </p>
            <Button asChild variant="outline">
              <Link to="/integrations">
                Explore integration plans
                <ArrowRight />
              </Link>
            </Button>
          </div>
          <Features
            items={[
              {
                title: "Workspace boundaries",
                text: "Identity and server-verified access must protect each organization.",
                icon: LockKeyhole,
              },
              {
                title: "Planned connections",
                text: "Explore intended channel and workflow connections without assuming availability.",
                icon: Network,
              },
            ]}
          />
        </div>
      </section>
      <section className="marketing-section section-tinted">
        <div className="marketing-two-columns">
          <div>
            <span className="marketing-eyebrow">CLEAR EXPECTATIONS</span>
            <h2>Find the right starting point.</h2>
            <p>OraOne access is free for everyone. No payment details are required.</p>
          </div>
          <div className="marketing-inquiry">
            <h3>Free access. Clear usage.</h3>
            <p>Real consumption will appear only when metering is connected.</p>
            <Button asChild>
              <Link to="/pricing">
                Pricing information
                <ArrowRight />
              </Link>
            </Button>
          </div>
        </div>
      </section>
      <FAQ
        items={[
          [
            "What can I explore today?",
            "The sample workspace includes AI Chat assistants, knowledge, conversations and widget configuration. It is a frontend preview; live identity, AI and delivery services are not connected.",
          ],
          [
            "Are all ten products available?",
            "No. AI Chat is the current product. Eight products are Planned and OraOne OS is a Long-term Vision.",
          ],
          [
            "Can I use my existing business knowledge?",
            "The knowledge interface is designed for business documentation and website content. Live ingestion and retrieval require the authoritative service integration.",
          ],
          [
            "Where can I find pricing?",
            "OraOne is free for everyone. Visit Pricing for access and usage information.",
          ],
          [
            "Does this preview create an account?",
            "No. Account access must be integrated with OraOne’s existing identity service before real sign-in or account creation is available.",
          ],
        ]}
      />
      <FinalCTA />
    </MarketingLayout>
  );
}

export function PublicPage({ title, pagePath }: Props) {
  const slug = pagePath.split("/").at(-1) || "";
  const product = pagePath.startsWith("/products/")
    ? products.find(
        (p) => p.slug === (slug === "ai-chat" ? "chat" : slug === "ai-voice" ? "voice" : slug),
      )
    : undefined;
  const solution = pagePath.startsWith("/solutions/")
    ? solutions.find((s) => s.slug === slug)
    : undefined;
  return (
    <MarketingLayout>
      <div className="marketing-inner">
        <nav className="marketing-breadcrumb" aria-label="Breadcrumb">
          <Link to="/">OraOne</Link>
          <span>/</span>
          <span>{title}</span>
        </nav>
        {product ? (
          <>
            <Heading
              eyebrow="THE ORAONE ECOSYSTEM"
              title={product.name}
              description={product.description}
            />
            <span className={`status-pill ${product.slug === "chat" ? "" : "planned"}`}>
              {product.status}
            </span>
            <CTAs sample />
            {product.slug === "chat" ? (
              <InterfacePreview compact />
            ) : (
              <div className="marketing-concept">
                <Layers />
                <h2>{product.short}</h2>
                <p>{product.description}</p>
                <div>
                  {product.capabilities.map((c) => (
                    <span key={c}>{c}</span>
                  ))}
                </div>
                <small>Conceptual product direction · Not released</small>
              </div>
            )}
            <section className="marketing-section">
              <h2>
                {product.slug === "chat"
                  ? "A connected assistant experience"
                  : "The intended product experience"}
              </h2>
              <Features
                items={product.capabilities.map((c, i) => ({
                  title: c,
                  text:
                    product.slug === "chat"
                      ? [
                          "Configure an assistant’s role and language around your business.",
                          "Prepare business content for retrieval through a connected knowledge service.",
                          "Keep customer context available to the people handling conversations.",
                          "Shape how your assistant appears on your website before deployment.",
                        ][i] || product.description
                      : `${c} is part of the planned ${product.short} direction. Specifications and release timing are not finalized.`,
                }))}
              />
              <Note>
                {product.slug === "chat"
                  ? "Current product is a portfolio designation, not operational readiness. This deployment is a frontend preview; live services need configuration."
                  : `${product.name} is ${product.status.toLowerCase()}. No release date or live availability is claimed.`}
              </Note>
            </section>
            <FAQ
              items={[
                [
                  `Is ${product.short} available?`,
                  product.slug === "chat"
                    ? "Explore its sample frontend today. Production readiness requires identity, model, storage and deployment integration."
                    : "This product is not released. Its roadmap direction is shown without implying live functionality.",
                ],
                [
                  "How does it connect to OraOne?",
                  "The portfolio is designed around shared identity and workspace context. Each service requires its own verified integration.",
                ],
              ]}
            />
            <section className="marketing-section">
              <h2>Explore the wider ecosystem</h2>
              <div className="marketing-related">
                {products
                  .filter((p) => p.slug !== product.slug)
                  .slice(0, 3)
                  .map((p) => (
                    <Link to={productPath(p.slug)} key={p.slug}>
                      {p.name}
                      <span>{p.status}</span>
                      <ArrowUpRight />
                    </Link>
                  ))}
              </div>
            </section>
          </>
        ) : solution ? (
          <>
            <Heading
              eyebrow={`SOLUTIONS / ${solution.name.toUpperCase()}`}
              title={solution.name}
              description={solution.heading}
            />
            <div className="marketing-two-columns solution-intro">
              <div>
                <h2>{solution.heading}</h2>
                <p>{solution.description}</p>
                <CTAs sample />
              </div>
              <div className="solution-visual">
                <solution.icon />
                <span>Customer context</span>
                <ArrowRight />
                <span>{solution.name}</span>
              </div>
            </div>
            <section className="marketing-section">
              <h2>Built around your next conversation</h2>
              <Features
                items={solution.features.map((f, i) => ({
                  title: f,
                  text:
                    [
                      solution.description,
                      "Keep your team’s understanding of customer needs in a shared workspace.",
                      "Review the intended workflow and connected-service requirements before going live.",
                    ][i] || solution.description,
                }))}
              />
            </section>
            <Note>
              Explore this workflow in the sample workspace. Live customer operations require
              connected services.
            </Note>
            <FinalCTA />
          </>
        ) : (
          <GenericPublicContent title={title} pagePath={pagePath} />
        )}
        {(product || solution) && <AppTour />}
      </div>
    </MarketingLayout>
  );
}

function GenericPublicContent({ title, pagePath }: Props) {
  if (pagePath === "/products" || pagePath === "/roadmap")
    return (
      <>
        <Heading
          eyebrow={pagePath === "/roadmap" ? "PRODUCT DIRECTION" : "ONE CONNECTED PORTFOLIO"}
          title={pagePath === "/roadmap" ? "OraOne roadmap" : "The OraOne ecosystem"}
          description="Ten products. One shared workspace vision. Explore current portfolio status and the direction ahead."
        />
        <ProductGrid />
        <Note>
          Statuses are portfolio labels. Planned products are not available; no release dates have
          been announced.
        </Note>
      </>
    );
  if (pagePath === "/solutions")
    return (
      <>
        <Heading
          eyebrow="BUILT AROUND YOUR BUSINESS"
          title="Solutions for your conversations"
          description="Explore how OraOne’s shared foundation can support customer service, sales and growing teams."
        />
        <div className="marketing-solution-grid">
          {solutions.map((s) => (
            <Link to={`/solutions/${s.slug}`} key={s.slug}>
              <s.icon />
              <h3>{s.name}</h3>
              <p>{s.description}</p>
              <ArrowUpRight />
            </Link>
          ))}
        </div>
        <FinalCTA />
      </>
    );
  if (pagePath === "/contact" || pagePath === "/demo" || pagePath === "/help/contact")
    return <ContactPage demo={pagePath === "/demo"} />;
  if (["/privacy", "/terms", "/cookies", "/acceptable-use", "/refund-policy"].includes(pagePath))
    return (
      <>
        <Heading
          eyebrow="TRUST & POLICIES"
          title={title}
          description="This policy is awaiting admin-approved legal content."
        />
        <Note>
          Draft content structure only. This page does not establish legal terms or commitments.
        </Note>
        <div className="marketing-policy">
          <h2>Policy review pending</h2>
          <p>
            The approved {title.toLowerCase()} text has not been supplied. Final scope, applicable
            entities, effective date and contact details must be confirmed before publication.
          </p>
          <div className="policy-outline">
            {[
              "Scope and applicability",
              "Responsibilities and rights",
              "Questions and contact",
            ].map((t) => (
              <div key={t}>
                <h3>{t}</h3>
                <p>Awaiting approved policy text.</p>
              </div>
            ))}
          </div>
          <Button asChild variant="outline">
            <Link to="/contact">
              Contact OraOne
              <ArrowRight />
            </Link>
          </Button>
        </div>
      </>
    );
  if (pagePath === "/pricing")
    return (
      <>
        <Heading
          eyebrow="FREE ACCESS"
          title="OraOne is free for everyone"
          description="No paid plans, subscriptions or payment details required."
        />
        <Note>
          Free access does not imply live service availability. This is a sample experience;
          identity and operational services are not connected.
        </Note>
        <Features
          items={[
            {
              title: "No payment required",
              text: "There is no checkout or payment collection in the current offering.",
              icon: Users,
            },
            {
              title: "Transparent consumption",
              text: "Real conversation, knowledge and model usage will appear only after metering is connected.",
              icon: MessageSquare,
            },
            {
              title: "An honest product roadmap",
              text: "AI Chat is the current product. Planned products are not released.",
              icon: Layers,
            },
          ]}
        />
        <CTAs sample />
        <FAQ
          items={[
            ["Is OraOne free?", "Yes. Access is free for everyone, with no payments."],
            [
              "Can I see real usage?",
              "Not in this disconnected preview. No consumption or quotas are invented.",
            ],
            [
              "Are planned products available?",
              "No. Their pages describe future direction, not working features.",
            ],
          ]}
        />
      </>
    );
  if (pagePath.startsWith("/docs") || pagePath.startsWith("/help"))
    return <Documentation title={title} pagePath={pagePath} />;
  if (pagePath === "/status")
    return (
      <>
        <Heading
          eyebrow="SERVICE VISIBILITY"
          title="Platform status"
          description="A transparent view of monitoring availability. Live service telemetry is not connected."
        />
        <Note>No uptime, incident-free status or production service health is asserted.</Note>
        <div className="marketing-status-list">
          {[
            "Application delivery",
            "Identity & access",
            "AI model services",
            "Knowledge ingestion",
            "Channel integrations",
          ].map((s) => (
            <div key={s}>
              <Network />
              <h3>{s}</h3>
              <span className="status-pill planned">Not monitored</span>
            </div>
          ))}
        </div>
        <section className="marketing-section">
          <h2>Incident history</h2>
          <p>
            Verified incident information is unavailable until the monitoring service is connected.
          </p>
        </section>
      </>
    );
  if (pagePath === "/changelog")
    return (
      <>
        <Heading
          eyebrow="PRODUCT UPDATES"
          title="OraOne changelog"
          description="A home for verified releases, improvements and fixes."
        />
        <div className="marketing-policy">
          <BookOpen />
          <h2>No verified release notes yet</h2>
          <p>
            Release dates and completed service milestones will appear here only after approval.
          </p>
          <Button asChild variant="outline">
            <Link to="/roadmap">
              Explore product direction
              <ArrowRight />
            </Link>
          </Button>
        </div>
      </>
    );
  if (pagePath === "/integrations")
    return (
      <>
        <Heading
          eyebrow="CONNECTED WORKFLOWS"
          title="OraOne integrations"
          description="Explore intended connections across your knowledge, customer channels and business workflows."
        />
        <Features
          items={[
            {
              title: "Business knowledge",
              text: "The AI Chat interface includes website and document source preparation. Live ingestion requires service configuration.",
              icon: BookOpen,
            },
            {
              title: "Customer channels",
              text: "Voice, WhatsApp and omnichannel experiences are planned products, not live channel connections.",
              icon: MessageSquare,
            },
            {
              title: "Business workflows",
              text: "Workflow Automation and marketplace extensions are part of the planned portfolio direction.",
              icon: Workflow,
            },
          ]}
        />
        <Note>
          No third-party integration is connected by this page. Provider setup, authorization and
          service validation are required.
        </Note>
        <Button asChild variant="outline">
          <Link to="/docs/integrations">
            Integration guidance
            <ArrowRight />
          </Link>
        </Button>
      </>
    );
  if (pagePath === "/security")
    return (
      <>
        <Heading
          eyebrow="TRUST THROUGH CLARITY"
          title="Security and control"
          description="OraOne’s intended security foundation keeps identity, workspace access and platform operations distinct."
        />
        <Features
          items={[
            {
              title: "Identity remains authoritative",
              text: "Account access must use the established identity service and verified sessions.",
              icon: LockKeyhole,
            },
            {
              title: "Workspace-scoped access",
              text: "Server authorization must enforce organization boundaries and membership roles.",
              icon: Users,
            },
            {
              title: "Private administration",
              text: "Internal operations require verified platform roles, separate from workspace roles.",
              icon: ShieldCheck,
            },
          ]}
        />
        <Note>
          This frontend preview does not prove production security controls, formal certifications
          or compliance approvals.
        </Note>
        <section className="marketing-section">
          <h2>Responsible questions deserve clear answers.</h2>
          <p>Ask about your organization’s requirements before connecting production data.</p>
          <Button asChild variant="outline">
            <Link to="/contact">
              Contact OraOne
              <ArrowRight />
            </Link>
          </Button>
        </section>
      </>
    );
  if (pagePath === "/about")
    return (
      <>
        <Heading
          eyebrow="ABOUT ORAONE"
          title="One platform. A shared purpose."
          description="OraOne is a unified AI business platform built around customer conversations, business knowledge and connected teams."
        />
        <img
          className="marketing-context-photo"
          src={teamPhoto}
          alt="Illustrative customer support team working together"
          width={1920}
          height={1024}
          loading="lazy"
        />
        <section className="marketing-section">
          <div className="marketing-two-columns">
            <div>
              <h2>
                Less fragmented context.
                <br />
                More thoughtful conversations.
              </h2>
            </div>
            <div>
              <p>
                Our product vision brings assistants, customer communication and business operations
                into one workspace, instead of treating every channel as an isolated tool.
              </p>
              <p>
                AI Chat is the starting point. The wider portfolio explores voice, messaging,
                automation and organization-wide control.
              </p>
            </div>
          </div>
        </section>
        <Features
          items={[
            {
              title: "Clarity over complexity",
              text: "One consistent workspace makes the next action easier to understand.",
              icon: Layers,
            },
            {
              title: "Knowledge with purpose",
              text: "Useful assistance starts with reliable business information.",
              icon: BookOpen,
            },
            {
              title: "People at the center",
              text: "Keep customers and teams connected to the context that matters.",
              icon: Users,
            },
          ]}
        />
        <FinalCTA />
      </>
    );
  return (
    <>
      <Heading
        eyebrow={pagePath === "/features" ? "A SHARED PRODUCT FOUNDATION" : "THE UNIFIED PLATFORM"}
        title={pagePath === "/features" ? "OraOne features" : "One platform for customer context"}
        description="Assistants, knowledge, conversations and teams—connected through one consistent workspace."
      />
      <InterfacePreview compact />
      <section className="marketing-section">
        <h2>
          {pagePath === "/features"
            ? "Explore the current AI Chat interface"
            : "A foundation that grows with your vision"}
        </h2>
        <Features
          items={[
            {
              title: "AI assistants",
              text: "Define a purpose, tone and language; review configuration before deployment.",
              icon: Bot,
            },
            {
              title: "Business knowledge",
              text: "Prepare documents and website content for a connected retrieval service.",
              icon: BookOpen,
            },
            {
              title: "Shared conversations",
              text: "Keep customer questions and team follow-up together in one inbox.",
              icon: MessageSquare,
            },
            {
              title: "Customer context",
              text: "Review customer profiles, lead details and conversation history.",
              icon: Users,
            },
            {
              title: "Widget experience",
              text: "Preview your website assistant’s appearance and greeting.",
              icon: Globe,
            },
            {
              title: "Portfolio direction",
              text: "Explore the eight planned products and long-term OraOne OS vision.",
              icon: Layers,
            },
          ]}
        />
        <Note>
          These are frontend experiences. Live identity, AI, persistence and deployment require
          integration with the authoritative services.
        </Note>
      </section>
      <FinalCTA />
    </>
  );
}

function ContactPage({ demo }: { demo: boolean }) {
  const [reviewed, setReviewed] = useState(false);
  return (
    <>
      <Heading
        eyebrow={demo ? "EXPLORE ORAONE TOGETHER" : "LET’S CONNECT"}
        title={demo ? "Request an OraOne demo" : "Contact OraOne"}
        description={
          demo
            ? "Tell us what you want to explore, from website assistants to a shared customer workspace."
            : "Share a question, a workspace requirement or the conversation you want to improve."
        }
      />
      <div className="marketing-contact-layout">
        <div>
          <h2>{demo ? "A conversation around your needs." : "Start with what matters to you."}</h2>
          <p>Include your business context and the workflows you want to discuss.</p>
          <Note>
            Message delivery is not connected. You can review your details, but no request will be
            sent.
          </Note>
        </div>
        <form
          className="marketing-contact-form"
          onSubmit={(e) => {
            e.preventDefault();
            setReviewed(true);
          }}
        >
          <label htmlFor="contact-name">Full name</label>
          <input id="contact-name" required autoComplete="name" placeholder="Your full name" />
          <label htmlFor="contact-email">Work email</label>
          <input
            id="contact-email"
            required
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
          />
          <label htmlFor="contact-company">
            Company <span>(optional)</span>
          </label>
          <input id="contact-company" autoComplete="organization" placeholder="Company name" />
          <label htmlFor="contact-message">
            {demo ? "What would you like to explore?" : "Your message"}
          </label>
          <textarea id="contact-message" required rows={5} placeholder="Tell us about your needs" />
          <Button type="submit">
            Review {demo ? "demo request" : "message"}
            <ArrowRight />
          </Button>
          {reviewed && (
            <div className="form-feedback" role="status">
              Your details passed the form review. Nothing was sent; delivery requires a connected
              contact service.
            </div>
          )}
          <p className="form-footnote">Draft form · No message delivery in this preview</p>
        </form>
      </div>
    </>
  );
}
function Documentation({ title, pagePath }: Props) {
  const [search, setSearch] = useState("");
  const links = manifest.filter(
    (r) => r.family === "public" && (r.path.startsWith("/docs") || r.path.startsWith("/help")),
  );
  const topic = pagePath === "/docs" || pagePath === "/help" ? "Getting started" : title;
  const knowledge = pagePath.includes("knowledge");
  const integration =
    pagePath.includes("integration") || pagePath.includes("api") || pagePath.includes("webhook");
  const account = pagePath.includes("account") || pagePath.includes("billing");
  const steps = knowledge
    ? [
        "Prepare reliable business content",
        "Review sources and permissions",
        "Connect the ingestion service",
        "Evaluate retrieval quality",
      ]
    : integration
      ? [
          "Identify the service and workspace scope",
          "Configure provider authorization in the authoritative service",
          "Verify delivery and failure handling",
          "Review logs before production use",
        ]
      : account
        ? [
            "Use the established identity flow",
            "Confirm organization membership",
            "Review your workspace access",
            "Review free access and connected usage",
          ]
        : [
            "Explore your workspace",
            "Define an assistant’s purpose",
            "Prepare your business knowledge",
            "Connect services before live testing",
          ];
  return (
    <>
      <Heading
        eyebrow={pagePath.startsWith("/help") ? "ORAONE HELP CENTER" : "ORAONE DOCUMENTATION"}
        title={title}
        description={`Practical guidance for ${topic.toLowerCase()}, with clear boundaries between this preview and live services.`}
      />
      <div className="marketing-docs">
        <aside>
          <label className="docs-search">
            <Search />
            <input
              aria-label="Search documentation"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Find a guide"
            />
          </label>
          <nav aria-label="Documentation">
            {links
              .filter((r) => r.title.toLowerCase().includes(search.toLowerCase()))
              .map((r) => (
                <Link to={r.path} key={r.path} activeProps={{ className: "docs-current" }}>
                  {r.title}
                </Link>
              ))}
          </nav>
          {!links.some((r) => r.title.toLowerCase().includes(search.toLowerCase())) && (
            <p>No matching guides.</p>
          )}
        </aside>
        <article>
          <h2>{topic}</h2>
          <p>
            {knowledge
              ? "Useful assistant responses start with accurate, up-to-date source content. Only add content your organization is permitted to use."
              : integration
                ? "Connections must be configured and verified in the authoritative OraOne services. This preview does not generate credentials, endpoints or successful delivery events."
                : account
                  ? "Identity, workspace permissions and workspace access must be read from their authoritative services. Frontend controls do not grant access."
                  : "Start in the sample workspace to understand the intended experience. Live assistant testing, ingestion and website deployment become available only after the required services are connected."}
          </p>
          <ol className="marketing-doc-steps">
            {steps.map((s, i) => (
              <li key={s}>
                <span>{i + 1}</span>
                <div>
                  <h3>{s}</h3>
                  <p>
                    {i === 0
                      ? "Review the intended configuration in the frontend preview."
                      : i === 1
                        ? "Confirm your business context and required access before proceeding."
                        : i === 2
                          ? "Complete and validate the authoritative service integration."
                          : "Use verified results rather than assuming a successful operation."}
                  </p>
                </div>
              </li>
            ))}
          </ol>
          <Note>
            Provider-specific credentials, API specifications, password policies and production
            runbooks must come from verified service configuration. They are not invented here.
          </Note>
          <Button asChild variant="outline">
            <Link to="/app">
              Explore sample workspace
              <ArrowUpRight />
            </Link>
          </Button>
        </article>
      </div>
    </>
  );
}
