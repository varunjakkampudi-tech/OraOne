import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Bot, MessageSquare } from "lucide-react";
import ProductTiles from "@/components/marketing/ProductTiles";
import WorkspaceIllustration from "@/components/marketing/WorkspaceIllustration";
import { useSEO } from "@/lib/seo";

export default function ProductsPage() {
  useSEO({
    title: "The OraOne ecosystem",
    description:
      "Explore OraOne AI Chat and the planned product portfolio in one connected workspace.",
  });
  return (
    <div className="mx-auto max-w-[1184px] px-5 py-10 sm:px-8">
      <header className="max-w-3xl">
        <p className="text-sm font-medium text-[#2563EB]">
          One connected portfolio
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight text-[#0F172A] sm:text-5xl">
          The OraOne ecosystem
        </h1>
        <p className="mt-5 text-lg leading-relaxed text-[#5B6B82]">
          Start with AI Chat. Explore the shared workspace vision for voice,
          messaging, automation and beyond.
        </p>
      </header>
      <section className="my-10 grid items-center gap-8 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-5 sm:p-8 lg:grid-cols-2">
        <div>
          <span className="rounded-full bg-[#EFF6FF] px-3 py-1 text-xs font-medium text-[#2563EB]">
            Product 1 · Active development
          </span>
          <h2 className="mt-5 text-3xl font-bold tracking-tight text-[#0F172A]">
            OraOne AI Chat Platform
          </h2>
          <p className="mt-4 text-base leading-relaxed text-[#5B6B82]">
            Bring website conversations, business knowledge and your team into
            one workspace.
          </p>
          <ul className="mt-5 space-y-3 text-sm text-[#334155]">
            {[
              [Bot, "Purposeful AI assistants"],
              [BookOpen, "Documents and website knowledge"],
              [MessageSquare, "Conversations, leads and a website widget"],
            ].map(([Icon, label]) => (
              <li key={label} className="flex items-center gap-3">
                <Icon size={18} className="text-[#2563EB]" />
                {label}
              </li>
            ))}
          </ul>
          <Link
            to="/products/ai-chat"
            data-testid="product-card-chat-cta"
            className="mt-6 inline-flex min-h-12 items-center gap-2 rounded-lg bg-[#2563EB] px-5 text-sm font-semibold text-white hover:bg-[#1D4ED8]"
          >
            Discover AI Chat <ArrowRight size={16} />
          </Link>
        </div>
        <WorkspaceIllustration />
      </section>
      <section>
        <div className="mb-7 max-w-2xl">
          <h2 className="text-2xl font-bold tracking-tight text-[#0F172A]">
            Ten products. One shared direction.
          </h2>
          <p className="mt-3 text-base leading-relaxed text-[#5B6B82]">
            Product numbers identify the portfolio, not a promised release
            order. Products 2–9 are planned; OraOne OS is the long-term vision.
          </p>
        </div>
        <ProductTiles />
      </section>
      <section className="mt-10 border-t border-[#E2E8F0] py-8">
        <h2 className="text-2xl font-bold tracking-tight text-[#0F172A]">
          Choose a thoughtful starting point.
        </h2>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-[#5B6B82]">
          OraOne access is currently free. Begin with your business knowledge
          and review your assistant before publishing.
        </p>
        <Link
          to="/signup"
          className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-lg border border-[#E2E8F0] px-4 text-sm font-semibold text-[#0F172A] hover:bg-[#F8FAFC]"
        >
          Create your workspace <ArrowRight size={16} />
        </Link>
      </section>
    </div>
  );
}
