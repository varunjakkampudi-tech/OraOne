import { useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Bot,
  Check,
  Code2,
  LockKeyhole,
  MessageSquare,
  Upload,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Brand } from "./shell";
import { onboardingSteps } from "@/lib/phase2";

const copy = [
  {
    title: "Welcome to OraOne",
    text: "A thoughtful starting point for your first business assistant.",
  },
  { title: "Make it yours", text: "Introduce yourself to the workspace." },
  { title: "Your business, together", text: "Give your workspace a name and a little context." },
  { title: "Start with a purpose", text: "What would you like your first assistant to help with?" },
  { title: "Meet your first assistant", text: "Define its name and the role it should play." },
  {
    title: "Give it reliable knowledge",
    text: "Prepare your business content, or come back to this later.",
  },
  {
    title: "Review before going live",
    text: "A configured model is required to test real responses.",
  },
  {
    title: "Bring OraOne to your website",
    text: "Installation follows verified assistant deployment.",
  },
  {
    title: "Your preview journey is complete",
    text: "Explore the sample workspace. No account or assistant has been created.",
  },
];
export function OnboardingPage({ pagePath }: { title: string; pagePath: string }) {
  const index = Math.max(
    0,
    onboardingSteps.findIndex((s) => s.path === pagePath),
  );
  const current = copy[index] || {
    title: "Welcome to OraOne",
    text: "Explore your setup journey.",
  };
  const [choice, setChoice] = useState("Customer support");
  const [draft, setDraft] = useState({ primary: "", secondary: "" });
  return (
    <div className="phase-onboarding">
      <header>
        <Link to="/" aria-label="OraOne home">
          <Brand />
        </Link>
        <Button asChild variant="ghost">
          <Link to="/app">
            Continue later
            <ArrowRight />
          </Link>
        </Button>
      </header>
      <main>
        <nav className="phase-onboarding-steps" aria-label="Setup steps">
          {onboardingSteps.map((s, i) => (
            <Link
              to={s.path}
              key={s.path}
              aria-current={i === index ? "step" : undefined}
              className={i === index ? "step-current" : i < index ? "step-reviewed" : ""}
            >
              <span>{i < index ? <Check /> : i + 1}</span>
              <strong>{s.title}</strong>
            </Link>
          ))}
        </nav>
        <section className="phase-onboarding-content">
          <span className="marketing-eyebrow">
            STEP {index + 1} OF {onboardingSteps.length}
          </span>
          <h1>{current.title}</h1>
          <p>{current.text}</p>
          <div className="form-feedback">
            Guided frontend preview · Drafts are not saved across pages. Live setup requires
            connected services.
          </div>
          {index === 0 ? (
            <div className="onboarding-intro">
              <Bot />
              <h2>One workspace. A clear next step.</h2>
              <ul>
                <li>
                  <Check />
                  Shape your assistant’s purpose
                </li>
                <li>
                  <Check />
                  Prepare trusted business knowledge
                </li>
                <li>
                  <Check />
                  Review the connection and deployment requirements
                </li>
              </ul>
            </div>
          ) : [1, 2, 4].includes(index) ? (
            <div className="onboarding-fields">
              <label htmlFor="setup-primary">
                {index === 1 ? "Display name" : index === 2 ? "Workspace name" : "Assistant name"}
              </label>
              <input
                id="setup-primary"
                value={draft.primary}
                onChange={(e) => setDraft((d) => ({ ...d, primary: e.target.value }))}
                placeholder={
                  index === 1 ? "Your name" : index === 2 ? "Your organization" : "Customer Support"
                }
              />
              <label htmlFor="setup-secondary">
                {index === 1
                  ? "Job title (optional)"
                  : index === 2
                    ? "Website (optional)"
                    : "Assistant purpose"}
              </label>
              <input
                id="setup-secondary"
                type={index === 2 ? "url" : "text"}
                value={draft.secondary}
                onChange={(e) => setDraft((d) => ({ ...d, secondary: e.target.value }))}
                placeholder={index === 2 ? "https://your-website.com" : "A brief description"}
              />
            </div>
          ) : index === 3 ? (
            <div className="onboarding-choice" role="group" aria-label="Assistant purpose">
              {["Customer support", "Lead qualification", "Customer onboarding", "Other"].map(
                (c) => (
                  <Button
                    key={c}
                    variant="outline"
                    aria-pressed={choice === c}
                    className={choice === c ? "choice-selected" : ""}
                    onClick={() => setChoice(c)}
                  >
                    <MessageSquare />
                    {c}
                    {choice === c && <Check />}
                  </Button>
                ),
              )}
            </div>
          ) : index === 5 ? (
            <div className="onboarding-knowledge">
              <BookOpen />
              <h2>Start with content you trust.</h2>
              <p>
                Prepare business documentation, FAQs or website content. Source ingestion is not
                connected, so no files will be uploaded here.
              </p>
              <Button variant="outline" disabled>
                <Upload />
                Upload unavailable
              </Button>
              <p className="form-footnote">
                Optional step · You can continue without knowledge setup.
              </p>
            </div>
          ) : index === 6 ? (
            <div className="onboarding-unavailable">
              <LockKeyhole />
              <h2>Model connection required</h2>
              <p>
                Real assistant responses can be evaluated after the authoritative model and
                knowledge services are connected.
              </p>
              <label htmlFor="setup-question">Question to prepare</label>
              <input id="setup-question" placeholder="What do customers often ask?" />
              <Button disabled>Test unavailable</Button>
            </div>
          ) : index === 7 ? (
            <div className="onboarding-unavailable">
              <Code2 />
              <h2>Deployment comes first</h2>
              <p>
                Your verified deployment service will generate the installation snippet. This
                preview does not invent embed code.
              </p>
              <ol>
                <li>Connect identity, model and knowledge services.</li>
                <li>Test and review assistant behavior.</li>
                <li>Deploy, then use the verified installation snippet.</li>
              </ol>
              <Button disabled>Installation code unavailable</Button>
            </div>
          ) : (
            <div className="onboarding-intro">
              <Bot />
              <h2>Ready to explore the experience.</h2>
              <p>
                You reviewed the setup journey. Account, workspace and assistant creation still
                require connected services.
              </p>
              <div className="setup-summary">
                <span>Identity</span>
                <strong>Not connected</strong>
                <span>AI & knowledge</span>
                <strong>Not connected</strong>
                <span>Deployment</span>
                <strong>Not connected</strong>
              </div>
            </div>
          )}
          <div className="onboarding-actions">
            {index > 0 && (
              <Button asChild variant="outline">
                <Link to={onboardingSteps[index - 1]?.path || "/onboarding"}>
                  <ArrowLeft />
                  Back
                </Link>
              </Button>
            )}
            <Button asChild>
              <Link
                to={
                  index === 8 ? "/app" : onboardingSteps[index + 1]?.path || "/onboarding/complete"
                }
              >
                {index === 8
                  ? "Explore workspace"
                  : index === 5
                    ? "Skip for now"
                    : "Continue preview"}
                <ArrowRight />
              </Link>
            </Button>
          </div>
        </section>
      </main>
    </div>
  );
}
