import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Shield,
  Lock,
  KeyRound,
  FileCheck2,
  Cloud,
  ClipboardList,
  ScrollText,
  Globe2,
  Server,
  Network,
  Users,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  AlertTriangle,
  Building2,
  Mail,
  Award,
  Eye,
  Database,
  Timer,
  GitMerge,
} from "lucide-react";
import { useSEO } from "@/lib/seo";

const fadeUp = {
  initial: { opacity: 0, y: 22 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.5 },
};

/* ─────────────────────────────────────────────────────────── */
/* Data                                                        */
/* ─────────────────────────────────────────────────────────── */

const CONTROL_CARDS = [
  {
    icon: Lock,
    title: "AES-256 Encryption at Rest",
    desc: "All customer data, conversation transcripts, lead records and knowledge-base files are encrypted at rest with AES-256.",
    badge: "Encryption",
    color: "#2563EB",
    bg: "#EFF6FF",
  },
  {
    icon: KeyRound,
    title: "TLS 1.3 In Transit",
    desc: "Every request between your browser, your customers, and the OraOne API is encrypted in transit using TLS 1.3 with modern cipher suites.",
    badge: "Transport",
    color: "#0EA5E9",
    bg: "#ECFEFF",
  },
  {
    icon: Users,
    title: "Role-Based Access Control",
    desc: "Granular permissions for Owner, Admin, Manager and Viewer. Restrict who can build agents, view conversations, export leads or change billing.",
    badge: "Access",
    color: "#7C3AED",
    bg: "#F5F3FF",
  },
  {
    icon: ScrollText,
    title: "Audit Logs",
    desc: "Every meaningful action — logins, agent edits, exports, integration changes — is logged with actor, IP, timestamp and old/new values.",
    badge: "Accountability",
    color: "#16A34A",
    bg: "#ECFDF5",
  },
  {
    icon: Timer,
    title: "Data Retention Controls",
    desc: "Configure retention windows per data type (conversations, transcripts, leads). Auto-purge on schedule. Right-to-delete honored within 30 days.",
    badge: "Lifecycle",
    color: "#F59E0B",
    bg: "#FEF3C7",
  },
  {
    icon: Cloud,
    title: "Secure Cloud Infrastructure",
    desc: "Hosted on AWS with VPC isolation, private subnets, security groups, IAM least-privilege and continuous CloudTrail / GuardDuty monitoring.",
    badge: "Infrastructure",
    color: "#DB2777",
    bg: "#FCE7F3",
  },
];

const COMPLIANCE = [
  {
    icon: FileCheck2,
    title: "GDPR Ready",
    status: "Active",
    statusColor: "#16A34A",
    statusBg: "#ECFDF5",
    desc: "Data subject access, rectification and deletion rights honored. DPA available for EU customers. Sub-processor list maintained.",
  },
  {
    icon: Globe2,
    title: "India DPDP Act Alignment",
    status: "Active",
    statusColor: "#16A34A",
    statusBg: "#ECFDF5",
    desc: "Aligned with the Digital Personal Data Protection Act, 2023. Consent management, purpose limitation and data principal rights.",
  },
  {
    icon: Award,
    title: "SOC 2 Type II",
    status: "In Progress",
    statusColor: "#F59E0B",
    statusBg: "#FEF3C7",
    desc: "SOC 2 Type II audit in progress with a Big-4 affiliated assessor. Letter of engagement available under NDA for Enterprise prospects.",
  },
  {
    icon: Shield,
    title: "ISO 27001",
    status: "Planned",
    statusColor: "#64748B",
    statusBg: "#F1F5F9",
    desc: "ISO 27001 certification planned for the post-launch year. Our ISMS controls already align with the standard.",
  },
  {
    icon: Building2,
    title: "HIPAA",
    status: "On Request",
    statusColor: "#7C3AED",
    statusBg: "#F5F3FF",
    desc: "BAA available for U.S. healthcare customers on Enterprise plans. Restricted-access deployment available on request.",
  },
  {
    icon: AlertTriangle,
    title: "PCI-DSS",
    status: "N/A",
    statusColor: "#64748B",
    statusBg: "#F1F5F9",
    desc: "OraOne does not store cardholder data. Billing is processed by a PCI-DSS Level 1 payment processor.",
  },
];

const SUB_PROCESSORS = [
  { name: "Amazon Web Services (AWS)", purpose: "Cloud hosting, storage, networking", region: "ap-south-1 / us-east-1", icon: Cloud },
  { name: "MongoDB Atlas", purpose: "Managed database (encrypted, VPC-peered)", region: "ap-south-1", icon: Database },
  { name: "Resend / Amazon SES", purpose: "Transactional emails (auth, notifications)", region: "us-east-1", icon: Mail },
  { name: "Sentry", purpose: "Error monitoring & performance", region: "EU", icon: Eye },
];

const PRACTICES = [
  { icon: GitMerge, title: "Secure SDLC", desc: "Code review, automated tests, dependency scanning and secret scanning on every PR." },
  { icon: Server, title: "Infrastructure-as-Code", desc: "Reproducible infrastructure with peer-reviewed Terraform & GitOps." },
  { icon: AlertTriangle, title: "Vulnerability Management", desc: "Continuous SCA + monthly third-party penetration testing scoped to public surfaces." },
  { icon: Database, title: "Backups & Recovery", desc: "Encrypted daily backups, point-in-time recovery, quarterly restoration drills." },
  { icon: Network, title: "Network Segmentation", desc: "Private subnets, least-privilege security groups, no direct database internet exposure." },
  { icon: ClipboardList, title: "Incident Response", desc: "24×7 on-call rotation, runbooks, post-mortems published to affected customers within 5 business days." },
];

const DATA_RIGHTS = [
  "Access — request a copy of your data in machine-readable format",
  "Rectification — correct inaccurate or incomplete data",
  "Erasure — request deletion of your account and associated data",
  "Portability — export your data to another provider",
  "Restriction — pause processing while you investigate",
  "Objection — opt out of specific processing activities",
];

/* ─────────────────────────────────────────────────────────── */
/* Page                                                        */
/* ─────────────────────────────────────────────────────────── */

export default function SecurityPage() {
  useSEO({
    title: "Security & Trust — Enterprise-Grade Protection",
    description:
      "How OraOne secures your data: AES-256 encryption, TLS 1.3, GDPR, India DPDP, SOC 2 (in progress), RBAC, audit logs, retention controls and sub-processor transparency.",
  });

  return (
    <div className="bg-white">
      {/* ============ HERO ============ */}
      <section className="relative pt-20 pb-14 sm:pt-24 sm:pb-16 overflow-hidden bg-gradient-to-b from-[#F8FAFC] via-white to-white border-b border-[#E2E8F0]">
        <div className="absolute inset-0 grid-bg opacity-50 [mask-image:radial-gradient(ellipse_at_center,black,transparent_70%)]" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-[1.4fr_1fr] gap-10 items-center">
            <motion.div {...fadeUp}>
              <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EFF6FF] text-[11px] font-bold tracking-[0.2em] text-[#2563EB]">
                <Shield size={11} /> SECURITY &amp; TRUST
              </span>
              <h1 className="mt-6 text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tighter text-[#0F172A] leading-[1.05]">
                Enterprise-grade security,
                <br />
                <span className="text-[#2563EB]">built from day one.</span>
              </h1>
              <p className="mt-5 text-base sm:text-lg text-[#475569] leading-relaxed max-w-2xl">
                We treat your data — and your customers&apos; data — like the most valuable
                asset in your business. Encrypted at every layer, governed by clear
                controls, and aligned with the regulations that matter to enterprise buyers.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Link
                  to="/contact"
                  className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white text-sm font-semibold shadow-[0_8px_24px_-6px_rgba(37,99,235,0.5)] transition-all"
                  data-testid="security-contact-cta"
                >
                  Request Security Documentation <ArrowRight size={14} />
                </Link>
                <a
                  href="#sub-processors"
                  className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-white border border-[#E2E8F0] hover:bg-[#F1F5F9] text-sm font-semibold text-[#0F172A] transition-colors"
                >
                  View sub-processors
                </a>
              </div>

              <div className="mt-8 flex flex-wrap items-center gap-4 text-[12.5px] text-[#475569]">
                {["AES-256", "TLS 1.3", "GDPR", "India DPDP", "SOC 2 (in progress)"].map((b) => (
                  <span key={b} className="inline-flex items-center gap-1.5">
                    <CheckCircle2 size={14} className="text-[#16A34A]" /> {b}
                  </span>
                ))}
              </div>
            </motion.div>

            {/* Right — vault illustration */}
            <motion.div
              {...fadeUp}
              className="hidden lg:flex justify-center"
            >
              <SecurityVault />
            </motion.div>
          </div>
        </div>
      </section>

      {/* ============ CONTROLS ============ */}
      <section className="py-16 sm:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto mb-12">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F1F5F9] text-[11px] font-bold tracking-[0.18em] text-[#475569] border border-[#E2E8F0] uppercase">
              <Sparkles size={11} /> Security Controls
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter text-[#0F172A]">
              The controls protecting your data.
            </h2>
            <p className="mt-4 text-[#64748B] leading-relaxed">
              Every layer of the OraOne stack is built with defence-in-depth.
              Here are the controls you can rely on today.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {CONTROL_CARDS.map((c, i) => (
              <motion.div
                key={c.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.05 }}
                transition={{ delay: i * 0.05 }}
                className="rounded-2xl border border-[#E2E8F0] bg-white p-6 hover:border-[#2563EB]/30 hover:shadow-premium transition-all"
              >
                <div className="flex items-center justify-between mb-4">
                  <div
                    className="size-11 rounded-xl grid place-items-center"
                    style={{ background: c.bg }}
                  >
                    <c.icon size={20} style={{ color: c.color }} />
                  </div>
                  <span
                    className="text-[10px] font-bold tracking-[0.16em] uppercase px-2 py-1 rounded-md"
                    style={{ background: c.bg, color: c.color }}
                  >
                    {c.badge}
                  </span>
                </div>
                <h3 className="text-[15px] font-semibold text-[#0F172A]">{c.title}</h3>
                <p className="mt-2 text-[13px] text-[#64748B] leading-relaxed">{c.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ COMPLIANCE ============ */}
      <section className="py-16 sm:py-20 bg-[#F8FAFC] border-y border-[#E2E8F0]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto mb-12">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white text-[11px] font-bold tracking-[0.18em] text-[#475569] border border-[#E2E8F0] uppercase">
              <FileCheck2 size={11} /> Compliance &amp; Certifications
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter text-[#0F172A]">
              Compliance, transparently tracked.
            </h2>
            <p className="mt-4 text-[#64748B] leading-relaxed">
              We&apos;re honest about where we are. Active, in-progress and planned —
              all called out clearly.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {COMPLIANCE.map((c, i) => (
              <motion.div
                key={c.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.05 }}
                transition={{ delay: i * 0.05 }}
                className="rounded-2xl border border-[#E2E8F0] bg-white p-6"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="size-11 rounded-xl bg-[#EFF6FF] grid place-items-center">
                    <c.icon size={20} className="text-[#2563EB]" />
                  </div>
                  <span
                    className="text-[10px] font-bold tracking-[0.16em] uppercase px-2 py-1 rounded-md"
                    style={{ background: c.statusBg, color: c.statusColor }}
                  >
                    {c.status}
                  </span>
                </div>
                <h3 className="text-[15px] font-semibold text-[#0F172A]">{c.title}</h3>
                <p className="mt-2 text-[13px] text-[#64748B] leading-relaxed">{c.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ============ PRACTICES ============ */}
      <section className="py-16 sm:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="grid lg:grid-cols-[1fr_1.4fr] gap-10 items-start">
            <div>
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F1F5F9] text-[11px] font-bold tracking-[0.18em] text-[#475569] border border-[#E2E8F0] uppercase">
                <ScrollText size={11} /> Engineering Practices
              </span>
              <h2 className="mt-4 text-3xl sm:text-4xl font-bold tracking-tighter text-[#0F172A] leading-tight">
                How we ship safely,
                <br />
                every day.
              </h2>
              <p className="mt-4 text-[#64748B] leading-relaxed">
                Security isn&apos;t an audit you pass once. It&apos;s a set of habits — code
                review, automated scanning, peer-reviewed infrastructure and 24/7
                incident response — that we live every day.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {PRACTICES.map((p) => (
                <div
                  key={p.title}
                  className="rounded-2xl border border-[#E2E8F0] bg-white p-5"
                >
                  <div className="size-10 rounded-xl bg-[#EFF6FF] grid place-items-center mb-3">
                    <p.icon size={18} className="text-[#2563EB]" />
                  </div>
                  <p className="text-[14px] font-semibold text-[#0F172A]">{p.title}</p>
                  <p className="mt-1.5 text-[12.5px] text-[#64748B] leading-snug">{p.desc}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ============ DATA RIGHTS ============ */}
      <section className="py-16 sm:py-20 bg-[#0F172A] text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="grid lg:grid-cols-2 gap-10 items-center">
            <div>
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-[11px] font-bold tracking-[0.18em] text-white/80 uppercase">
                <Users size={11} /> Your Rights
              </span>
              <h2 className="mt-4 text-3xl sm:text-4xl font-bold tracking-tighter leading-tight">
                You own your data.
                <br />
                Always.
              </h2>
              <p className="mt-4 text-white/70 leading-relaxed max-w-md">
                Under GDPR, the India DPDP Act and our own customer commitments, you have
                full rights to your data. Exercise them anytime via your account or by
                emailing{" "}
                <a className="underline" href="mailto:privacy@oraone.in">privacy@oraone.in</a>.
              </p>
            </div>
            <ul className="space-y-3">
              {DATA_RIGHTS.map((r) => (
                <li
                  key={r}
                  className="flex items-start gap-3 p-4 rounded-xl bg-white/5 border border-white/10"
                >
                  <span className="size-6 rounded-full bg-[#2563EB] grid place-items-center shrink-0 mt-0.5">
                    <CheckCircle2 size={14} className="text-white" />
                  </span>
                  <span className="text-[14px] text-white/90 leading-relaxed">{r}</span>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </section>

      {/* ============ SUB-PROCESSORS ============ */}
      <section id="sub-processors" className="py-16 sm:py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="text-center max-w-2xl mx-auto mb-10">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#F1F5F9] text-[11px] font-bold tracking-[0.18em] text-[#475569] border border-[#E2E8F0] uppercase">
              <Network size={11} /> Sub-Processor Transparency
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter text-[#0F172A]">
              Who else touches your data.
            </h2>
            <p className="mt-4 text-[#64748B] leading-relaxed">
              We use a minimal, intentional set of sub-processors. Each is bound by a DPA
              and only handles the data strictly needed for their role.
            </p>
          </motion.div>

          <div className="rounded-3xl border border-[#E2E8F0] bg-white overflow-hidden">
            <div className="grid grid-cols-12 px-5 sm:px-7 py-4 bg-[#F8FAFC] border-b border-[#E2E8F0] text-[11px] font-bold tracking-[0.16em] text-[#64748B] uppercase">
              <div className="col-span-5">Sub-Processor</div>
              <div className="col-span-5">Purpose</div>
              <div className="col-span-2 text-right">Region</div>
            </div>
            {SUB_PROCESSORS.map((s) => (
              <div
                key={s.name}
                className="grid grid-cols-12 items-center px-5 sm:px-7 py-4 border-b border-[#E2E8F0] last:border-b-0 hover:bg-[#F8FAFC] transition-colors"
              >
                <div className="col-span-5 flex items-center gap-3">
                  <div className="size-9 rounded-xl bg-[#EFF6FF] grid place-items-center shrink-0">
                    <s.icon size={16} className="text-[#2563EB]" />
                  </div>
                  <span className="text-[13.5px] font-semibold text-[#0F172A]">{s.name}</span>
                </div>
                <div className="col-span-5 text-[13px] text-[#475569]">{s.purpose}</div>
                <div className="col-span-2 text-right text-[12px] text-[#64748B]">{s.region}</div>
              </div>
            ))}
          </div>

          <p className="mt-4 text-[12px] text-[#64748B] text-center">
            We&apos;ll notify customers at least 30 days before adding a new sub-processor.
            Subscribe to updates via your account settings.
          </p>
        </div>
      </section>

      {/* ============ CTA ============ */}
      <section className="pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            {...fadeUp}
            className="relative rounded-3xl p-10 sm:p-14 overflow-hidden text-white shadow-premium-lg"
            style={{ background: "linear-gradient(135deg, #2563EB 0%, #1E40AF 100%)" }}
          >
            <div className="absolute -top-20 -right-20 size-80 rounded-full bg-white/10" />
            <div className="absolute -bottom-32 -left-32 size-96 rounded-full bg-white/5" />
            <div className="relative grid lg:grid-cols-[1.4fr_1fr] gap-8 items-center">
              <div>
                <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tighter leading-tight">
                  Building enterprise procurement?
                  <br />
                  We&apos;ve done it before.
                </h2>
                <p className="mt-4 text-white/85 max-w-2xl leading-relaxed">
                  We can share our SOC 2 letter of engagement, DPA, security
                  questionnaire (SIG / CAIQ), penetration test summary and architecture
                  diagrams under NDA. Procurement teams welcome.
                </p>
              </div>
              <div className="flex flex-wrap gap-3 lg:justify-end">
                <Link
                  to="/contact"
                  className="px-5 py-3 rounded-xl bg-white text-[#2563EB] font-semibold text-sm hover:bg-white/90 transition-colors inline-flex items-center gap-2"
                >
                  Contact Security <ArrowRight size={14} />
                </Link>
                <a
                  href="mailto:security@oraone.in"
                  className="px-5 py-3 rounded-xl border border-white/30 hover:bg-white/10 font-semibold text-sm transition-colors inline-flex items-center gap-2"
                >
                  <Mail size={14} /> security@oraone.in
                </a>
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────── */
/* Decorative SVG                                              */
/* ─────────────────────────────────────────────────────────── */

function SecurityVault() {
  return (
    <div className="relative w-full max-w-md aspect-square">
      <div className="absolute inset-0 rounded-[2rem] bg-gradient-to-br from-[#EFF6FF] to-white border border-[#E2E8F0] shadow-premium-lg" />
      <div className="absolute inset-6 rounded-[1.75rem] bg-white border border-[#E2E8F0] flex flex-col">
        <div className="px-5 pt-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="size-8 rounded-lg bg-[#0F172A] grid place-items-center">
              <Shield size={16} className="text-white" />
            </div>
            <div>
              <p className="text-[12px] font-bold text-[#0F172A]">OraOne Trust Center</p>
              <p className="text-[10px] text-[#64748B]">Live status</p>
            </div>
          </div>
          <span className="inline-flex items-center gap-1.5 text-[10px] font-bold text-[#16A34A]">
            <span className="size-1.5 rounded-full bg-[#16A34A]" /> SECURE
          </span>
        </div>
        <div className="px-5 pt-5 grid grid-cols-2 gap-2.5">
          {[
            { label: "AES-256", icon: Lock, color: "#2563EB", bg: "#EFF6FF" },
            { label: "TLS 1.3", icon: KeyRound, color: "#0EA5E9", bg: "#ECFEFF" },
            { label: "RBAC", icon: Users, color: "#7C3AED", bg: "#F5F3FF" },
            { label: "Audit Logs", icon: ScrollText, color: "#16A34A", bg: "#ECFDF5" },
            { label: "GDPR", icon: FileCheck2, color: "#F59E0B", bg: "#FEF3C7" },
            { label: "DPDP", icon: Globe2, color: "#DB2777", bg: "#FCE7F3" },
          ].map((b) => (
            <div
              key={b.label}
              className="rounded-xl border border-[#E2E8F0] p-3 flex items-center gap-2.5"
            >
              <div className="size-8 rounded-lg grid place-items-center shrink-0" style={{ background: b.bg }}>
                <b.icon size={14} style={{ color: b.color }} />
              </div>
              <span className="text-[11.5px] font-semibold text-[#0F172A]">{b.label}</span>
            </div>
          ))}
        </div>
        <div className="px-5 pt-4 mt-auto pb-5">
          <div className="rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] px-3 py-2.5 flex items-center justify-between">
            <span className="text-[11px] font-semibold text-[#475569]">SOC 2 Type II</span>
            <span className="text-[10px] font-bold text-[#F59E0B]">IN PROGRESS</span>
          </div>
        </div>
      </div>
    </div>
  );
}
