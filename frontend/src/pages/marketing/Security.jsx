import { Link } from "react-router-dom";
import {
  ShieldCheck,
  Users,
  Lock,
  FileSearch,
  Database,
  ArrowUpRight,
} from "lucide-react";
import { useSEO } from "@/lib/seo";

const CONTROLS = [
  {
    icon: Users,
    title: "Server-side authorization",
    text: "PostgreSQL-backed platform roles and tenant memberships govern API access. Browser role checks are presentation, not the security boundary.",
  },
  {
    icon: Lock,
    title: "Authentication and credentials",
    text: "Local password authentication uses password hashing and email-code verification. Provider credentials stay on the backend. Cognito requires separately verified deployment configuration.",
  },
  {
    icon: FileSearch,
    title: "Audit records",
    text: "Application mutations emit actor/resource audit records. Audit snapshots are persisted in PostgreSQL; release reviews must check the coverage of privileged actions.",
  },
  {
    icon: Database,
    title: "Data and storage",
    text: "PostgreSQL and MinIO provide the self-hosted data layer. Encryption at rest, retention, backups and recovery depend on operator configuration and verification.",
  },
];

export default function SecurityPage() {
  useSEO({
    title: "Security and data handling",
    description:
      "OraOne application security controls, deployment responsibilities and private vulnerability reporting. No certification or production uptime guarantee is claimed.",
  });
  return (
    <div className="mx-auto max-w-[1184px] px-5 py-12 sm:px-8">
      <header className="max-w-3xl">
        <span className="inline-flex items-center gap-2 text-sm font-semibold text-blue-700">
          <ShieldCheck size={18} /> Security and trust
        </span>
        <h1 className="mt-4 text-3xl font-bold tracking-tight text-slate-950 sm:text-5xl">
          Security and data handling
        </h1>
        <p className="mt-5 text-base leading-7 text-slate-600">
          Understand the application's controls and the checks required for your
          deployment. Test results are not a certification or a production
          service guarantee.
        </p>
      </header>
      <section
        className="mt-10 grid gap-5 md:grid-cols-2"
        aria-label="Application controls"
      >
        {CONTROLS.map(({ icon: Icon, title, text }) => (
          <article
            key={title}
            className="rounded-lg border border-slate-200 bg-white p-6"
          >
            <Icon size={22} className="text-blue-700" aria-hidden="true" />
            <h2 className="mt-4 text-lg font-semibold text-slate-950">
              {title}
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
          </article>
        ))}
      </section>
      <section className="mt-8 rounded-lg border border-slate-200 bg-slate-50 p-6">
        <h2 className="text-xl font-semibold text-slate-950">
          Deployment and assurance
        </h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Verify TLS, storage encryption, access policies, outbound network
          restrictions, retention and restore procedures in the actual hosting
          environment. No SOC 2 or ISO certification, audit engagement, HIPAA
          agreement, GDPR/DPDP compliance determination, uptime SLA or
          penetration-test program is asserted here.
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Provider availability, processing location and contractual obligations
          must be confirmed for the services you enable. OraOne currently offers
          free access without a payment integration.
        </p>
      </section>
      <section className="mt-8 rounded-lg bg-slate-900 p-6 text-white sm:p-8">
        <h2 className="text-xl font-semibold">
          Report a vulnerability privately
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
          Use the repository's private GitHub reporting channel. Do not post
          passwords, tokens, private customer data or sensitive exploit details
          in public issues.
        </p>
        <a
          href="https://github.com/varunjakkampudi-tech/OraOne/security/advisories/new"
          target="_blank"
          rel="noopener noreferrer"
          className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold hover:bg-blue-500"
        >
          Private security report <ArrowUpRight size={16} />
        </a>
        <Link
          to="/privacy"
          className="ml-5 inline-flex min-h-11 items-center text-sm font-medium text-slate-200 hover:text-white"
        >
          Privacy policy
        </Link>
      </section>
    </div>
  );
}
