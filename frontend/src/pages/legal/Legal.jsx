import React from "react";
import { useSEO } from "@/lib/seo";

function LegalShell({ title, updated, children }) {
  return (
    <div className="py-20 bg-white">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tighter text-[#0F172A]">{title}</h1>
        <p className="mt-3 text-sm text-[#64748B]">Last updated: {updated}</p>
        <div className="mt-10 prose prose-slate max-w-none text-[#475569] space-y-6">{children}</div>
      </div>
    </div>
  );
}

export function Privacy() {
  useSEO({ title: "Privacy Policy", description: "How OraOne collects, uses and protects your data." });
  return (
    <LegalShell title="Privacy Policy" updated="January 26, 2026">
      <p>At OraOne, we value your privacy. This policy explains how we collect, use, and safeguard your information.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">1. Information We Collect</h2>
      <p>Account data (name, email, company), usage data (interactions with the platform), and conversation data captured by your AI agents on your behalf.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">2. How We Use Information</h2>
      <p>To deliver the OraOne service, improve product quality, prevent fraud, and provide customer support.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">3. Data Sharing</h2>
      <p>We never sell your data. We share with sub-processors strictly necessary to operate the service (cloud hosting, telephony, analytics) under data-processing agreements.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">4. Data Security</h2>
      <p>Encrypted in transit (TLS 1.3) and at rest (AES-256). Audit logs, access controls and OWASP-aligned security practices are enforced.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">5. Your Rights</h2>
      <p>You may access, export, correct, or delete your data at any time via your account settings or by contacting privacy@oraone.in.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">6. Cookies</h2>
      <p>We use first-party cookies to keep you logged in and analytics cookies (anonymised) to improve the product. See our Cookie Policy.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">7. Changes to This Policy</h2>
      <p>We will notify you of material changes via email or product notice 30 days in advance.</p>
    </LegalShell>
  );
}

export function Terms() {
  useSEO({ title: "Terms of Service", description: "The terms governing your use of the OraOne platform." });
  return (
    <LegalShell title="Terms of Service" updated="January 26, 2026">
      <p>By using OraOne, you agree to the following terms and conditions.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">1. Acceptance of Terms</h2>
      <p>Your access to and use of the service is conditioned on your acceptance of and compliance with these terms.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">2. Use of Services</h2>
      <p>You agree to use the service in compliance with applicable laws, including telephony and data-protection laws (TCPA, GDPR, DPDP).</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">3. User Responsibilities</h2>
      <p>You are responsible for the content of conversations your AI agents handle and for obtaining necessary consents from end-users.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">4. Intellectual Property</h2>
      <p>OraOne and its content remain the property of OraOne Technologies. You retain ownership of your business data.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">5. Limitation of Liability</h2>
      <p>OraOne shall not be liable for indirect, incidental, or consequential damages arising from use of the service.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">6. Termination</h2>
      <p>Either party may terminate the agreement with 30 days' notice. Beta accounts may be terminated immediately for misuse.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">7. Governing Law</h2>
      <p>These terms are governed by the laws of India.</p>
    </LegalShell>
  );
}

export function Cookie() {
  useSEO({ title: "Cookie Policy", description: "How OraOne uses cookies and similar technologies." });
  return (
    <LegalShell title="Cookie Policy" updated="January 26, 2026">
      <p>We use cookies to improve your experience and analyse site traffic.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">1. What Are Cookies</h2>
      <p>Cookies are small text files stored on your device by your browser when you visit a website.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">2. How We Use Cookies</h2>
      <p>Essential cookies for authentication, preference cookies for settings, analytics cookies for product improvement.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">3. Types of Cookies</h2>
      <ul className="list-disc pl-6 space-y-1">
        <li>Strictly Necessary — required for the service to function</li>
        <li>Performance — anonymised analytics</li>
        <li>Functional — remember your preferences</li>
      </ul>
      <h2 className="text-xl font-semibold text-[#0F172A]">4. Managing Cookies</h2>
      <p>You can disable cookies in your browser settings. Some features may not work properly with cookies disabled.</p>
      <h2 className="text-xl font-semibold text-[#0F172A]">5. Third-Party Cookies</h2>
      <p>We use Google Analytics, Microsoft Clarity and PostHog. These providers have their own privacy policies.</p>
    </LegalShell>
  );
}

export function DataDeletion() {
  useSEO({ title: "Data Deletion Request", description: "Request deletion of your OraOne account and data." });
  const [email, setEmail] = React.useState("");
  const [sent, setSent] = React.useState(false);
  return (
    <LegalShell title="Data Deletion Request" updated="January 26, 2026">
      <p>We're sorry to see you go. You can request deletion of your data here. Please confirm your email is correct.</p>
      <ul className="list-disc pl-6 space-y-1">
        <li>All your data will be permanently deleted.</li>
        <li>AI agents, conversations and leads will be removed.</li>
        <li>Integrations will be disconnected.</li>
        <li>This action cannot be reversed.</li>
      </ul>
      {sent ? (
        <div className="mt-6 p-5 rounded-2xl bg-green-50 border border-green-200 text-green-700 text-sm">
          We've received your request. Your data will be deleted within 30 days. A confirmation email has been sent.
        </div>
      ) : (
        <form
          onSubmit={(e) => { e.preventDefault(); setSent(true); }}
          className="mt-6 flex flex-col sm:flex-row gap-3"
        >
          <input
            required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            data-testid="data-deletion-email"
            className="flex-1 rounded-xl border border-[#E2E8F0] bg-white px-4 py-3 text-sm focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10"
          />
          <button type="submit" data-testid="data-deletion-submit" className="px-5 py-3 rounded-xl bg-[#DC2626] hover:bg-[#B91C1C] text-white text-sm font-semibold">
            Send Request
          </button>
        </form>
      )}
    </LegalShell>
  );
}
