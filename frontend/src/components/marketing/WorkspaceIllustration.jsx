import {
  BookOpen,
  Bot,
  Inbox,
  LayoutDashboard,
  MessageSquare,
  Users,
} from "lucide-react";
import { OraMark } from "./Logo";

/** A deliberately illustrative workspace, never customer data or live metrics. */
export default function WorkspaceIllustration({ compact = false }) {
  return (
    <figure
      className={`overflow-hidden rounded-lg border border-[#E2E8F0] bg-white ${compact ? "mt-8" : "w-full"}`}
    >
      <div className="flex items-center justify-between gap-3 bg-[#0F172A] px-4 py-3 text-white">
        <span className="flex items-center gap-2 text-sm font-semibold">
          <OraMark size={24} /> OraOne
        </span>
        <span className="text-[11px] text-[#CBD5E1]">Illustrative preview</span>
      </div>
      <div className="grid grid-cols-[100px_minmax(0,1fr)] sm:grid-cols-[120px_minmax(0,1fr)]">
        <div
          className="space-y-4 border-r border-[#E2E8F0] px-3 py-5 text-[11px] text-[#64748B]"
          aria-hidden="true"
        >
          {[
            [LayoutDashboard, "Overview"],
            [Inbox, "Inbox"],
            [Bot, "AI Chat"],
            [BookOpen, "Knowledge"],
            [Users, "Team"],
          ].map(([Icon, label]) => (
            <div
              key={label}
              className={`flex items-center gap-2 ${label === "Overview" ? "text-[#2563EB]" : ""}`}
            >
              <Icon size={13} />
              {label}
            </div>
          ))}
        </div>
        <div className="min-w-0 space-y-4 bg-[#F8FAFC] p-4 sm:p-5">
          <div>
            <p className="text-sm font-bold text-[#0F172A]">
              Your workspace, together
            </p>
            <p className="mt-1 text-[11px] leading-relaxed text-[#64748B]">
              Knowledge, assistants and customer conversations.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {[
              { icon: Bot, title: "AI assistants" },
              { icon: BookOpen, title: "Business knowledge" },
            ].map(({ icon: Icon, title }) => (
              <div
                key={title}
                className="rounded-md border border-[#E2E8F0] bg-white p-3"
              >
                <Icon size={17} className="mb-3 text-[#2563EB]" />
                <p className="text-[11px] font-semibold text-[#334155]">
                  {title}
                </p>
                <div
                  className="mt-2 h-1.5 w-3/4 rounded bg-[#E2E8F0]"
                  aria-hidden="true"
                />
              </div>
            ))}
          </div>
          <div className="rounded-md border border-[#E2E8F0] bg-white p-3">
            <p className="flex items-center gap-2 text-[11px] font-semibold text-[#334155]">
              <MessageSquare size={14} className="text-[#2563EB]" /> Customer
              conversations
            </p>
            <div className="mt-3 space-y-2" aria-hidden="true">
              {["w-full", "w-4/5", "w-3/5"].map((width) => (
                <div
                  key={width}
                  className={`h-2 rounded bg-[#F1F5F9] ${width}`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
      <figcaption className="border-t border-[#E2E8F0] px-4 py-2.5 text-[11px] text-[#64748B]">
        Interface illustration · No live customer data
      </figcaption>
    </figure>
  );
}
