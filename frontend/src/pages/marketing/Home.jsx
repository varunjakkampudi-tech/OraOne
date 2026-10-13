import { Link } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Bot,
  MessageSquare,
  Users,
} from "lucide-react";
import WorkspaceIllustration from "@/components/marketing/WorkspaceIllustration";
import ProductTiles from "@/components/marketing/ProductTiles";
import { useSEO } from "@/lib/seo";
import { HOME } from "@/constants/testIds";

const features = [
  {
    icon: Bot,
    title: "An assistant with a purpose",
    text: "Shape its instructions, tone and knowledge around the questions your customers ask.",
  },
  {
    icon: BookOpen,
    title: "Grounded in your knowledge",
    text: "Bring approved documents and website content into your assistant’s knowledge base.",
  },
  {
    icon: MessageSquare,
    title: "People stay in the loop",
    text: "Review conversations and customer context together, with a clear next step for your team.",
  },
];
const steps = [
  {
    title: "Create your workspace",
    text: "Bring your business and team into one place.",
  },
  {
    title: "Shape your assistant",
    text: "Define its purpose and connect reliable knowledge.",
  },
  {
    title: "Review, then connect",
    text: "Test your assistant before publishing the widget to your website.",
  },
];
const faq = [
  [
    "What can I use today?",
    "OraOne AI Chat Platform brings together website assistants, knowledge, conversations, leads and usage in one workspace.",
  ],
  [
    "Are all ten products available?",
    "No. AI Chat is the active product. Products 2–9 are planned, and OraOne OS is the long-term vision.",
  ],
  [
    "Can I use my business knowledge?",
    "Add documents and website sources, choose which knowledge your assistant can use, and review its answers before publishing.",
  ],
  [
    "Is a payment method required?",
    "No. Access is currently free. Usage and consumption remain visible without payment collection.",
  ],
];
function SectionHeading({ title, children }) {
  return (
    <div className="mb-8 max-w-2xl">
      <h2 className="text-2xl font-bold tracking-tight text-[#0F172A] sm:text-3xl">
        {title}
      </h2>
      {children && (
        <p className="mt-3 text-base leading-relaxed text-[#64748B]">
          {children}
        </p>
      )}
    </div>
  );
}
export default function HomePage() {
  useSEO({
    title: "One connected workspace for AI chat",
    description:
      "Bring business knowledge, AI assistants and customer conversations together with OraOne AI Chat Platform.",
  });
  return (
    <div className="bg-white">
      <section className="overflow-hidden bg-[#0F172A] text-white">
        <div className="mx-auto grid max-w-[1184px] items-center gap-10 px-5 py-12 sm:px-8 sm:py-16 lg:grid-cols-[0.9fr_1.1fr] lg:gap-12">
          <div>
            <Link
              to="/products/ai-chat"
              className="inline-flex min-h-11 items-center gap-2 rounded-full border border-white/20 px-4 text-sm text-[#DBEAFE]"
            >
              Meet OraOne AI Chat <ArrowRight size={15} />
            </Link>
            <h1 className="mt-7 text-5xl font-bold tracking-tight sm:text-6xl">
              OraOne
            </h1>
            <h2 className="mt-4 text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
              Customer conversations.
              <br />
              One connected workspace.
            </h2>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-[#CBD5E1]">
              Your knowledge, AI assistants and team—together for more
              thoughtful customer experiences.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                to="/signup"
                data-testid={HOME.heroCtaPrimary}
                className="inline-flex min-h-12 items-center gap-2 rounded-lg bg-[#2563EB] px-5 text-sm font-semibold text-white hover:bg-[#1D4ED8]"
              >
                Get started <ArrowUpRight size={17} />
              </Link>
              <Link
                to="/contact"
                data-testid={HOME.heroCtaSecondary}
                className="inline-flex min-h-12 items-center gap-2 rounded-lg border border-white/30 px-5 text-sm font-semibold hover:bg-white/10"
              >
                Request a demo <ArrowRight size={17} />
              </Link>
            </div>
            <p className="mt-4 text-sm text-[#CBD5E1]">
              Free access · No payment method required
            </p>
          </div>
          <WorkspaceIllustration />
        </div>
      </section>
      <section
        className="border-b border-[#E2E8F0]"
        data-testid={HOME.trustSection}
      >
        <div className="mx-auto grid max-w-[1184px] grid-cols-2 gap-5 px-5 py-6 sm:px-8 lg:grid-cols-4">
          {[...features, { icon: Users, title: "Connected teams" }].map(
            ({ icon: Icon, title }) => (
              <div
                key={title}
                className="flex items-center gap-3 text-sm font-medium text-[#334155]"
              >
                <Icon size={20} className="shrink-0 text-[#2563EB]" />
                {title}
              </div>
            ),
          )}
        </div>
      </section>
      <section
        className="mx-auto max-w-[1184px] px-5 py-12 sm:px-8"
        data-testid={HOME.demoSection}
      >
        <SectionHeading title="Your knowledge. A more helpful conversation.">
          Give your website a business-aware assistant, then keep your team and
          customer context close.
        </SectionHeading>
        <div className="grid gap-7 sm:grid-cols-3">
          {features.map(({ icon: Icon, title, text }) => (
            <article key={title}>
              <Icon size={24} className="mb-4 text-[#2563EB]" />
              <h3 className="text-base font-semibold text-[#0F172A]">
                {title}
              </h3>
              <p className="mt-2 text-base leading-relaxed text-[#64748B]">
                {text}
              </p>
            </article>
          ))}
        </div>
        <Link
          to="/products/ai-chat"
          className="mt-8 inline-flex min-h-11 items-center gap-2 rounded-lg border border-[#E2E8F0] px-4 text-sm font-semibold text-[#0F172A] hover:bg-[#F8FAFC]"
        >
          Discover AI Chat <ArrowRight size={16} />
        </Link>
      </section>
      <section className="border-y border-[#E2E8F0] bg-[#F8FAFC]">
        <div className="mx-auto max-w-[1184px] px-5 py-12 sm:px-8">
          <SectionHeading title="A thoughtful path to your first assistant." />
          <ol className="grid gap-8 sm:grid-cols-3">
            {steps.map(({ title, text }, index) => (
              <li key={title}>
                <span className="text-sm font-semibold text-[#2563EB]">
                  0{index + 1}
                </span>
                <h3 className="mt-3 text-lg font-semibold text-[#0F172A]">
                  {title}
                </h3>
                <p className="mt-2 text-base leading-relaxed text-[#64748B]">
                  {text}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>
      <section className="mx-auto max-w-[1184px] px-5 py-12 sm:px-8">
        <SectionHeading title="One account. Ten connected product visions.">
          Start with AI Chat. Explore the roadmap for voice, messaging,
          automation and beyond.
        </SectionHeading>
        <ProductTiles />
      </section>
      <section
        className="border-y border-[#E2E8F0] bg-[#F8FAFC]"
        data-testid={HOME.pricingSnippet}
      >
        <div className="mx-auto grid max-w-[1184px] gap-6 px-5 py-12 sm:px-8 md:grid-cols-2">
          <SectionHeading title="Free access. Clear usage.">
            No payment details are required. Review your workspace’s real
            consumption as you use OraOne.
          </SectionHeading>
          <div className="flex items-center md:justify-end">
            <Link
              to="/pricing"
              data-testid={HOME.pricingSnippetCta}
              className="inline-flex min-h-12 items-center gap-2 rounded-lg border border-[#E2E8F0] bg-white px-5 text-sm font-semibold text-[#0F172A]"
            >
              Access and usage <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>
      <section className="mx-auto grid max-w-[1184px] gap-8 px-5 py-12 sm:px-8 lg:grid-cols-[1fr_1.5fr]">
        <SectionHeading title="A little more clarity." />
        <div>
          {faq.map(([question, answer]) => (
            <details key={question} className="border-b border-[#E2E8F0] py-5">
              <summary className="cursor-pointer text-base font-semibold text-[#0F172A]">
                {question}
              </summary>
              <p className="mt-3 text-base leading-relaxed text-[#64748B]">
                {answer}
              </p>
            </details>
          ))}
        </div>
      </section>
      <section className="border-t border-[#E2E8F0] bg-[#F8FAFC] px-5 py-12 text-center">
        <h2 className="text-3xl font-bold tracking-tight text-[#0F172A]">
          Bring your workspace together.
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-base leading-relaxed text-[#64748B]">
          Start with OraOne AI Chat and build around the conversations that
          matter.
        </p>
        <Link
          to="/signup"
          className="mt-6 inline-flex min-h-12 items-center gap-2 rounded-lg bg-[#2563EB] px-6 text-sm font-semibold text-white hover:bg-[#1D4ED8]"
        >
          Create your account <ArrowUpRight size={16} />
        </Link>
      </section>
    </div>
  );
}
