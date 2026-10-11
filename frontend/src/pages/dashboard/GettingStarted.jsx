import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Rocket,
  FolderKanban,
  Bot,
  BookOpen,
  LayoutGrid,
  MessagesSquare,
  Users,
  CheckCircle2,
  Circle,
  ArrowRight,
  Sparkles,
  PartyPopper,
} from "lucide-react";
import { api } from "@/lib/api";
import { useProjects } from "@/lib/projects";
import { useTour } from "@/lib/tour";
import { PageHeader, Card, Badge, PrimaryButton, GhostButton } from "@/components/dashboard/kit";

/* Pull a count out of either a {items,total} envelope or a bare array. */
const countOf = (data) => {
  if (Array.isArray(data)) return data.length;
  if (data && typeof data === "object") {
    if (typeof data.total === "number") return data.total;
    if (Array.isArray(data.items)) return data.items.length;
  }
  return 0;
};

function useSetupState() {
  const { projects } = useProjects();
  const [state, setState] = useState({
    loading: true,
    agents: 0,
    knowledgeBases: 0,
    websites: 0,
    widgets: 0,
    conversations: 0,
    members: 0,
  });

  useEffect(() => {
    let active = true;
    (async () => {
      const calls = [
        api.get("/agents", { params: { limit: 1 } }),
        api.get("/knowledge-bases", { params: { limit: 1 } }),
        api.get("/websites", { params: { limit: 1 } }),
        api.get("/widgets"),
        api.get("/conversations", { params: { limit: 1 } }),
        api.get("/team/members").catch(() => null),
      ];
      const r = await Promise.allSettled(calls);
      if (!active) return;
      const d = (i) => (r[i] && r[i].status === "fulfilled" && r[i].value ? r[i].value.data : null);
      setState({
        loading: false,
        agents: countOf(d(0)),
        knowledgeBases: countOf(d(1)),
        websites: countOf(d(2)),
        widgets: countOf(d(3)),
        conversations: countOf(d(4)),
        members: countOf(d(5)),
      });
    })();
    return () => {
      active = false;
    };
  }, []);

  return { ...state, projects: projects?.length || 0 };
}

export default function GettingStarted() {
  const s = useSetupState();
  const { start } = useTour();

  const steps = useMemo(
    () => [
      {
        key: "project",
        icon: FolderKanban,
        title: "Create your workspace project",
        desc: "Projects keep each assistant, its knowledge and channels neatly organised.",
        done: s.projects > 0,
        to: "/app/dashboard",
        cta: "Open projects",
      },
      {
        key: "agent",
        icon: Bot,
        title: "Build your first AI agent",
        desc: "Spin up a chat agent with a guided, no-code builder.",
        done: s.agents > 0,
        to: "/app/create-agent",
        cta: "Create an agent",
      },
      {
        key: "knowledge",
        icon: BookOpen,
        title: "Add your knowledge",
        desc: "Upload documents or crawl your website so answers stay grounded and accurate.",
        done: s.knowledgeBases > 0 || s.websites > 0,
        to: "/app/knowledge-base",
        cta: "Add knowledge",
      },
      {
        key: "widget",
        icon: LayoutGrid,
        title: "Deploy a widget",
        desc: "Drop a chat bubble on your site with a single snippet — no engineering required.",
        done: s.widgets > 0,
        to: "/app/widgets",
        cta: "Set up a widget",
      },
      {
        key: "chat",
        icon: MessagesSquare,
        title: "Test your agent",
        desc: "Chat with your assistant to see grounded answers and source citations in action.",
        done: s.conversations > 0,
        to: "/app/chat",
        cta: "Open chat",
      },
      {
        key: "team",
        icon: Users,
        title: "Invite your team",
        desc: "Bring teammates in to collaborate on agents, inboxes and analytics.",
        done: s.members > 1,
        optional: true,
        to: "/app/team",
        cta: "Invite teammates",
      },
    ],
    [s]
  );

  const required = steps.filter((x) => !x.optional);
  const doneCount = required.filter((x) => x.done).length;
  const total = required.length;
  const pct = total ? Math.round((doneCount / total) * 100) : 0;
  const allDone = doneCount >= total;
  const nextStep = steps.find((x) => !x.done);
  const cta = allDone
    ? { to: "/app/dashboard", label: "Explore dashboard" }
    : nextStep
    ? { to: nextStep.to, label: `Continue: ${nextStep.cta}` }
    : null;

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6">
      <PageHeader
        eyebrow="Onboarding"
        icon={Rocket}
        title="Getting started"
        subtitle="A guided path from zero to a live AI assistant — everything is linked, no tutorials required."
        actions={
          <div className="flex items-center gap-2">
            <GhostButton onClick={start} data-testid="getting-started-tour">
              <Sparkles size={15} />
              Take the tour
            </GhostButton>
            <GhostButton as={Link} to="/app/guide" data-testid="getting-started-guide">
              <BookOpen size={15} />
              Step-by-step guide
            </GhostButton>
            {cta ? (
              <PrimaryButton as={Link} to={cta.to} data-testid="getting-started-next">
                {cta.label}
                <ArrowRight size={16} />
              </PrimaryButton>
            ) : null}
          </div>
        }
      />

      {/* Progress summary */}
      <Card className="p-5" data-testid="getting-started-progress">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-2xl bg-gradient-to-br from-[#EFF4FF] to-[#ECFEFF] text-[#2563EB] ring-1 ring-[#DBEAFE]">
              {allDone ? <PartyPopper size={22} /> : <Sparkles size={22} />}
            </span>
            <div>
              <p className="text-sm font-bold text-[#0F172A]">
                {allDone ? "You're all set up! 🎉" : "Setup progress"}
              </p>
              <p className="text-xs text-[#64748B]">
                {allDone
                  ? "Every essential step is complete. Your assistant is ready for customers."
                  : `${doneCount} of ${total} essential steps complete`}
              </p>
            </div>
          </div>
          <Badge tone={allDone ? "green" : "indigo"}>{pct}%</Badge>
        </div>
        <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-[#EEF2F7]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#2563EB] to-[#06B6D4] transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      </Card>

      {/* Steps */}
      <div className="space-y-3">
        {steps.map((step, i) => {
          const Icon = step.icon;
          return (
            <Card
              key={step.key}
              className="flex items-center gap-4 p-4"
              data-testid={`getting-started-step-${step.key}`}
            >
              <span
                className={
                  "grid size-11 shrink-0 place-items-center rounded-2xl ring-1 " +
                  (step.done
                    ? "bg-[#DCFCE7] text-[#15803D] ring-[#BBF7D0]"
                    : "bg-[#EFF4FF] text-[#2563EB] ring-[#E0E7FF]")
                }
              >
                <Icon size={20} />
              </span>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-bold text-[#0F172A]">
                    {i + 1}. {step.title}
                  </p>
                  {step.optional && <Badge tone="slate">Optional</Badge>}
                  {step.done && <Badge tone="green">Done</Badge>}
                </div>
                <p className="mt-0.5 text-xs leading-snug text-[#64748B]">{step.desc}</p>
              </div>

              <div className="shrink-0">
                {step.done ? (
                  <CheckCircle2 size={22} className="text-[#16A34A]" />
                ) : (
                  <GhostButton as={Link} to={step.to} data-testid={`getting-started-cta-${step.key}`}>
                    {step.cta}
                    <ArrowRight size={15} />
                  </GhostButton>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      <p className="flex items-center gap-2 px-1 text-xs text-[#94A3B8]">
        <Circle size={12} />
        Progress updates automatically as you complete each step.
      </p>
    </div>
  );
}
