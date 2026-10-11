import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Logo } from "./Logo";
import { api, formatApiError } from "@/lib/api";
import SimpleIcon from "@/components/ui/SimpleIcon";
import { toast } from "sonner";

const socialLinks = [
  { label: "LinkedIn", slug: "linkedin" },
  { label: "X", slug: "x" },
  { label: "YouTube", slug: "youtube" },
  { label: "GitHub", slug: "github" },
];

const columns = [
  {
    title: "Products",
    links: [
      { to: "/products", label: "Chat Agent" },
      { to: "/templates", label: "Templates" },
    ],
  },
  {
    title: "Solutions",
    links: [
      { to: "/solutions", label: "Industries" },
      { to: "/solutions", label: "Use Cases" },
      { to: "/solutions", label: "For Teams" },
      { to: "/solutions", label: "For Enterprise" },
    ],
  },
  {
    title: "Resources",
    links: [
      { to: "/documentation", label: "Documentation" },
      { to: "/case-studies", label: "Case Studies" },
      { to: "/integrations", label: "Integrations" },
      { to: "/security", label: "Security & Trust" },
      { to: "/contact", label: "Help Center" },
    ],
  },
  {
    title: "Company",
    links: [
      { to: "/about", label: "About Us" },
      { to: "/contact", label: "Contact" },
      { to: "/about", label: "Careers" },
      { to: "/about", label: "Partners" },
    ],
  },
];

export default function Footer() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  const subscribe = async (e) => {
    e.preventDefault();
    if (!email) return;
    setBusy(true);
    try {
      await api.post("/newsletter", { email });
      toast.success("You're in! Welcome to OraOne updates.");
      setEmail("");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Subscription failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <footer className="bg-[#0F172A] text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
          <div className="lg:col-span-4">
            <Logo light className="h-10" />
            <p className="mt-5 text-sm text-white/70 leading-relaxed max-w-sm">
              AI chat agents for your website. Automate conversations, capture leads, book appointments — grow your business 24/7.
            </p>
            <form onSubmit={subscribe} className="mt-6 flex gap-2 max-w-sm">
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                data-testid="footer-newsletter-email"
                className="flex-1 min-w-0 bg-white/5 border border-white/15 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/50 focus:outline-none focus:border-[#3B82F6] focus:ring-4 focus:ring-[#3B82F6]/10"
              />
              <button
                type="submit"
                disabled={busy}
                data-testid="footer-newsletter-submit"
                className="px-4 py-2.5 rounded-xl bg-[#2563EB] hover:bg-[#1D4ED8] text-sm font-medium transition-colors disabled:opacity-60"
              >
                {busy ? "..." : "Subscribe"}
              </button>
            </form>
            <div className="mt-6 flex items-center gap-3">
              {socialLinks.map((social) => (
                <a
                  key={social.label}
                  href="#"
                  aria-label={social.label}
                  className="size-9 grid place-items-center rounded-full bg-white/5 hover:bg-white/10 transition-colors"
                >
                  <SimpleIcon slug={social.slug} size={16} color="#FFFFFF" title={social.label} />
                </a>
              ))}
            </div>
          </div>

          <div className="lg:col-span-8 grid grid-cols-2 md:grid-cols-4 gap-8">
            {columns.map((col) => (
              <div key={col.title}>
                <h3 className="text-sm font-semibold text-white mb-4">{col.title}</h3>
                <ul className="space-y-3">
                  {col.links.map((l, i) => (
                    <li key={i}>
                      <Link to={l.to} className="text-sm text-white/65 hover:text-white transition-colors">
                        {l.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-white/55">© 2026 OraOne Technologies Pvt. Ltd. All rights reserved.</p>
          <div className="flex items-center gap-5">
            <Link to="/privacy" className="text-xs text-white/55 hover:text-white">Privacy Policy</Link>
            <Link to="/terms" className="text-xs text-white/55 hover:text-white">Terms of Service</Link>
            <Link to="/security" className="text-xs text-white/55 hover:text-white">Security</Link>
            <Link to="/cookie-policy" className="text-xs text-white/55 hover:text-white">Cookie Policy</Link>
            <Link to="/data-deletion" className="text-xs text-white/55 hover:text-white">Data Deletion</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
