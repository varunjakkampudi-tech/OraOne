import React from "react";
import { Link } from "react-router-dom";
import {
  BookOpen,
  Bot,
  BookMarked,
  PlayCircle,
  Rocket,
  ArrowRight,
  CheckCircle2,
  MessageSquare,
  Code2,
} from "lucide-react";
import { PageHeader, Card, Badge, PrimaryButton, GhostButton } from "@/components/dashboard/kit";
import { useTour } from "@/lib/tour";

function Step({ number, icon: Icon, title, children, to, cta }) {
  return (
    <Card className="p-5">
      <div className="flex items-start gap-4">
        <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-[#EFF4FF] text-[#2563EB] ring-1 ring-[#E0E7FF] font-bold">
          {Icon ? <Icon size={20} /> : number}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-[#0F172A]">
            Step {number}. {title}
          </p>
          <div className="mt-1.5 space-y-1.5 text-[13px] leading-relaxed text-[#475569]">{children}</div>
          {to ? (
            <GhostButton as={Link} to={to} className="mt-3">
              {cta}
              <ArrowRight size={15} />
            </GhostButton>
          ) : null}
        </div>
      </div>
    </Card>
  );
}

export default function Guide() {
  const { start } = useTour();
  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <PageHeader
        eyebrow="Help"
        icon={BookOpen}
        title="Create, test & deploy an agent"
        subtitle="A short walkthrough of the whole journey — from a blank workspace to a live AI agent on your website."
        actions={
          <PrimaryButton onClick={start} data-testid="guide-start-tour">
            <PlayCircle size={16} />
            Take the interactive tour
          </PrimaryButton>
        }
      />

      <Step number={1} icon={Bot} title="Create your agent" to="/app/agents/new" cta="Create an agent">
        <p>
          Go to <strong>AI Agents → Create Agent</strong>, choose <strong>Chat Agent</strong>,
          then fill in the business name and purpose. OraOne auto-saves as you go.
        </p>
      </Step>

      <Step number={2} icon={BookMarked} title="Add knowledge (optional but recommended)" to="/app/knowledge-base" cta="Add knowledge">
        <p>
          Upload documents or crawl your website so the agent answers from your real content instead of generic
          replies. You can skip this and add it later — the agent still works with its base instructions.
        </p>
      </Step>

      <Step number={3} icon={Rocket} title="Deploy the agent" to="/app/agents" cta="Go to AI Agents">
        <p>
          Open your agent and go to <strong>Review &amp; Deploy → Deploy Agent</strong>. This turns the agent{" "}
          <Badge tone="green" className="mx-0.5">active</Badge> — it can now hold conversations.
        </p>
      </Step>

      <Step number={4} icon={PlayCircle} title="Test it before going live">
        <p>You have two ways to try it out, no live website needed:</p>
        <ul className="list-disc space-y-1 pl-4">
          <li>
            <strong>Quick test:</strong> open{" "}
            <Link to="/app/chat" className="font-semibold text-[#2563EB] hover:underline">
              Conversations
            </Link>{" "}
            and start a chat with your agent directly inside the dashboard.
          </li>
          <li>
            <strong>Widget test:</strong> open your agent's{" "}
            <Link to="/app/agents" className="font-semibold text-[#2563EB] hover:underline">
              Channels &amp; Deploy
            </Link>{" "}
            page and click <strong>Test widget</strong> — this loads the real chat bubble right on that page
            (it publishes the widget automatically the first time, so it always works).
          </li>
        </ul>
      </Step>

      <Step number={5} icon={Code2} title="Put it on your website" cta="Copy embed code from Channels & Deploy">
        <p>
          Once you're happy with the answers, copy the one-line <code className="rounded bg-[#F1F5F9] px-1 py-0.5 text-[12px]">&lt;script&gt;</code>{" "}
          snippet from the same Channels &amp; Deploy page and paste it before <code className="rounded bg-[#F1F5F9] px-1 py-0.5 text-[12px]">&lt;/body&gt;</code>{" "}
          on your site, then click <strong>Publish &amp; go live</strong> (if not already live) and{" "}
          <strong>Verify install</strong> to confirm it's reachable.
        </p>
      </Step>

      <Card className="flex items-center gap-3 p-4">
        <CheckCircle2 size={20} className="shrink-0 text-[#16A34A]" />
        <p className="text-[13px] text-[#475569]">
          That's it — your agent is live. Watch real conversations come in under{" "}
          <Link to="/app/conversations" className="font-semibold text-[#2563EB] hover:underline">
            Conversations
          </Link>{" "}
          and captured leads under{" "}
          <Link to="/app/leads" className="font-semibold text-[#2563EB] hover:underline">
            Leads
          </Link>
          .
        </p>
      </Card>

      <div className="flex justify-center pt-2">
        <PrimaryButton as={Link} to="/app/getting-started">
          <MessageSquare size={16} />
          Back to Getting Started checklist
        </PrimaryButton>
      </div>
    </div>
  );
}
