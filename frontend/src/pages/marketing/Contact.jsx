import React, { useState } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  Mail,
  Phone,
  MapPin,
  User,
  Calendar,
  Clock,
  ChevronDown,
  Check,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { useSEO } from "@/lib/seo";

const COUNTRY_CODES = [
  { code: "+91", flag: "🇮🇳", name: "India" },
  { code: "+1", flag: "🇺🇸", name: "United States" },
  { code: "+44", flag: "🇬🇧", name: "United Kingdom" },
  { code: "+971", flag: "🇦🇪", name: "United Arab Emirates" },
  { code: "+61", flag: "🇦🇺", name: "Australia" },
  { code: "+65", flag: "🇸🇬", name: "Singapore" },
  { code: "+49", flag: "🇩🇪", name: "Germany" },
  { code: "+33", flag: "🇫🇷", name: "France" },
  { code: "+81", flag: "🇯🇵", name: "Japan" },
  { code: "+86", flag: "🇨🇳", name: "China" },
];

const COMPANY_SIZES = [
  "1 – 10 employees",
  "11 – 50 employees",
  "51 – 200 employees",
  "201 – 500 employees",
  "501 – 1,000 employees",
  "1,000+ employees",
];

const BENEFITS = [
  "See OraOne in action with real use cases",
  "Get expert guidance tailored to your business",
  "Discover how you can save time and increase conversions",
];

export default function ContactPage() {
  useSEO({
    title: "Book a Demo",
    description:
      "Book a personalized demo and see how OraOne answers customers instantly, captures every lead, and works around the clock on your website.",
  });

  const [form, setForm] = useState({
    name: "",
    email: "",
    country: COUNTRY_CODES[0],
    phone: "",
    company_size: "",
    message: "",
    demo_time: "",
  });
  const [countryOpen, setCountryOpen] = useState(false);
  const [sizeOpen, setSizeOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const update = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);

    // Backend's ContactIn accepts name/email/company/message/type — bundle the
    // additional demo-specific fields into a structured message string.
    const lines = [
      `Phone: ${form.country.code} ${form.phone || "(not provided)"}`,
      form.company_size ? `Company size: ${form.company_size}` : null,
      form.demo_time ? `Preferred demo time: ${form.demo_time}` : null,
      "",
      `Goals / challenges:`,
      form.message,
    ].filter(Boolean);

    try {
      await api.post("/contact", {
        name: form.name,
        email: form.email,
        company: form.company_size || null,
        message: lines.join("\n"),
        type: "demo",
      });
      toast.success("Thanks! Our team will reach out within 24 hours.");
      setForm({
        name: "",
        email: "",
        country: COUNTRY_CODES[0],
        phone: "",
        company_size: "",
        message: "",
        demo_time: "",
      });
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail) || "Failed to submit");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative bg-[#F8FAFC] py-20 overflow-hidden">
      {/* Subtle ambient blobs */}
      <div
        className="absolute -top-32 -left-32 w-[480px] h-[480px] rounded-full pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(37,99,235,0.12), transparent 65%)" }}
      />
      <div
        className="absolute -bottom-32 -right-32 w-[520px] h-[520px] rounded-full pointer-events-none"
        style={{ background: "radial-gradient(circle, rgba(124,58,237,0.10), transparent 65%)" }}
      />
      {/* sparkle accents */}
      <Sparkle className="absolute top-32 right-[18%] text-[#2563EB]/40" size={14} />
      <Sparkle className="absolute top-[55%] left-[44%] text-[#7C3AED]/35" size={12} />
      <Sparkle className="absolute bottom-32 left-[8%] text-[#2563EB]/30" size={16} />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-[1fr_1.05fr] gap-14 lg:gap-20">
        {/* ============================== LEFT ============================== */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="lg:pt-6"
        >
          <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EFF6FF] text-[11px] font-bold tracking-[0.2em] text-[#2563EB]">
            <span className="size-1.5 rounded-full bg-[#2563EB]" />
            BOOK A DEMO
          </span>

          <h1 className="mt-6 text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-[#0F172A] leading-[1.05]">
            Let&apos;s talk about<br />
            your business
          </h1>

          <p className="mt-5 text-[#64748B] text-base sm:text-lg leading-relaxed max-w-md">
            Book a personalized demo and see how OraOne answers customers instantly, captures every
            lead, and works around the clock on your website.
          </p>

          {/* Contact info cards */}
          <div className="mt-10 space-y-4 max-w-md">
            <InfoCard icon={Mail} label="Email" value="sales@oraone.in" />
            <InfoCard icon={Clock} label="Response time" value="Within 24 hours" />
            <InfoCard icon={MapPin} label="Office" value="Mumbai, India" />
          </div>

          {/* Why book a demo? */}
          <div
            className="mt-10 rounded-2xl p-6 border border-[#DBEAFE] max-w-md"
            style={{ background: "linear-gradient(135deg,#EFF6FF 0%,#F5F3FF 100%)" }}
          >
            <h3 className="text-[15px] font-semibold text-[#2563EB]">Why book a demo?</h3>
            <ul className="mt-4 space-y-3">
              {BENEFITS.map((b) => (
                <li key={b} className="flex items-start gap-3">
                  <span className="mt-0.5 size-5 rounded-full bg-[#2563EB] grid place-items-center shrink-0">
                    <Check size={12} className="text-white" strokeWidth={3} />
                  </span>
                  <span className="text-[14px] text-[#334155] leading-snug">{b}</span>
                </li>
              ))}
            </ul>
          </div>
        </motion.div>

        {/* ============================== RIGHT (FORM) ============================== */}
        <motion.form
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          onSubmit={submit}
          className="bg-white rounded-3xl border border-[#E2E8F0] shadow-[0_24px_60px_-24px_rgba(15,23,42,0.18)] p-8 sm:p-10 space-y-6"
          noValidate
        >
          {/* Full Name */}
          <FormField label="Full Name" required>
            <div className="relative">
              <User size={17} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => update("name", e.target.value)}
                placeholder="Enter your full name"
                data-testid="contact-name"
                className={fieldCls("pl-11")}
              />
            </div>
          </FormField>

          {/* Email Address */}
          <FormField label="Email Address" required>
            <div className="relative">
              <Mail size={17} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                placeholder="Enter your email address"
                data-testid="contact-email"
                className={fieldCls("pl-11")}
              />
            </div>
          </FormField>

          {/* Phone Number */}
          <FormField label="Phone Number" required>
            <div className="relative flex">
              {/* Country code button */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setCountryOpen((o) => !o)}
                  data-testid="contact-country-code"
                  className="h-[52px] pl-11 pr-8 rounded-l-xl border border-[#E2E8F0] border-r-0 bg-white text-sm font-medium text-[#0F172A] hover:bg-[#F8FAFC] transition-colors flex items-center gap-2"
                >
                  <Phone size={17} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
                  <span className="text-base leading-none">{form.country.flag}</span>
                  <span>{form.country.code}</span>
                  <ChevronDown size={14} className="text-[#94A3B8]" />
                </button>
                {countryOpen && (
                  <div className="absolute z-20 mt-2 left-0 w-60 max-h-72 overflow-y-auto rounded-xl border border-[#E2E8F0] bg-white shadow-premium-lg py-2">
                    {COUNTRY_CODES.map((c) => (
                      <button
                        type="button"
                        key={c.code + c.name}
                        onClick={() => {
                          update("country", c);
                          setCountryOpen(false);
                        }}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-[#0F172A] hover:bg-[#F8FAFC] transition-colors"
                      >
                        <span className="text-base">{c.flag}</span>
                        <span className="font-medium w-12">{c.code}</span>
                        <span className="text-[#64748B] text-[13px] truncate">{c.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <input
                type="tel"
                required
                value={form.phone}
                onChange={(e) => update("phone", e.target.value.replace(/[^\d\s-]/g, ""))}
                placeholder="Enter your phone number"
                data-testid="contact-phone"
                className="flex-1 min-w-0 h-[52px] px-4 rounded-r-xl border border-[#E2E8F0] bg-white text-sm text-[#0F172A] placeholder-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10 transition-all"
              />
            </div>
          </FormField>

          {/* Company Size */}
          <FormField label="Company Size">
            <div className="relative">
              <button
                type="button"
                onClick={() => setSizeOpen((o) => !o)}
                data-testid="contact-company-size"
                className={`w-full text-left ${fieldCls("pr-11")} flex items-center justify-between`}
              >
                <span className={form.company_size ? "text-[#0F172A]" : "text-[#94A3B8]"}>
                  {form.company_size || "Select company size"}
                </span>
                <ChevronDown
                  size={16}
                  className={`text-[#94A3B8] transition-transform ${sizeOpen ? "rotate-180" : ""}`}
                />
              </button>
              {sizeOpen && (
                <div className="absolute z-20 mt-2 left-0 right-0 max-h-72 overflow-y-auto rounded-xl border border-[#E2E8F0] bg-white shadow-premium-lg py-2">
                  {COMPANY_SIZES.map((s) => (
                    <button
                      type="button"
                      key={s}
                      onClick={() => {
                        update("company_size", s);
                        setSizeOpen(false);
                      }}
                      className="w-full text-left px-4 py-2.5 text-sm text-[#0F172A] hover:bg-[#F8FAFC] transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </FormField>

          {/* Message */}
          <FormField label="How can we help you?" required>
            <textarea
              required
              rows={4}
              value={form.message}
              onChange={(e) => update("message", e.target.value)}
              placeholder="Tell us about your goals or challenges"
              data-testid="contact-message"
              className="w-full rounded-xl border border-[#E2E8F0] bg-white px-4 py-3 text-sm text-[#0F172A] placeholder-[#94A3B8] resize-y min-h-[120px] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10 transition-all"
            />
          </FormField>

          {/* Preferred Demo Time */}
          <FormField label="Preferred Demo Time">
            <div className="relative">
              <Calendar size={17} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#94A3B8] pointer-events-none" />
              <input
                type="datetime-local"
                value={form.demo_time}
                onChange={(e) => update("demo_time", e.target.value)}
                data-testid="contact-demo-time"
                className={`${fieldCls("pl-11 pr-4")} ${form.demo_time ? "text-[#0F172A]" : "text-[#94A3B8]"}`}
              />
            </div>
          </FormField>

          {/* Security note */}
          <div className="flex items-center gap-2 text-[12.5px] text-[#64748B]">
            <ShieldCheck size={14} className="text-[#2563EB]" />
            Your information is secure and will never be shared.
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={busy}
            data-testid="contact-submit"
            className="group w-full inline-flex items-center justify-center gap-2.5 py-4 rounded-2xl bg-[#2563EB] hover:bg-[#1D4ED8] text-white font-semibold text-[15px] transition-all disabled:opacity-60 shadow-[0_18px_40px_-12px_rgba(37,99,235,0.55)]"
          >
            <Calendar size={17} />
            {busy ? "Sending..." : "Book a Demo"}
            <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
          </button>

          {/* Footer link */}
          <p className="text-center text-sm text-[#64748B]">
            Not sure yet?{" "}
            <Link
              to="/"
              data-testid="contact-learn-more"
              className="font-semibold text-[#2563EB] hover:underline inline-flex items-center gap-1"
            >
              Learn more about OraOne <ArrowRight size={14} />
            </Link>
          </p>
        </motion.form>
      </div>
    </div>
  );
}

/* --------------------------------- helpers --------------------------------- */

function fieldCls(extra = "") {
  return `w-full h-[52px] rounded-xl border border-[#E2E8F0] bg-white px-4 text-sm text-[#0F172A] placeholder-[#94A3B8] focus:border-[#2563EB] focus:outline-none focus:ring-4 focus:ring-[#2563EB]/10 transition-all ${extra}`;
}

function FormField({ label, required, children }) {
  return (
    <div>
      <label className="block text-[13px] font-semibold text-[#0F172A] mb-2">
        {label} {required && <span className="text-[#EF4444]">*</span>}
      </label>
      {children}
    </div>
  );
}

function InfoCard({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-4 p-4 rounded-2xl bg-white border border-[#E2E8F0] hover:border-[#CBD5E1] hover:shadow-premium transition-all">
      <div className="size-12 rounded-xl bg-[#EFF6FF] grid place-items-center shrink-0">
        <Icon size={20} className="text-[#2563EB]" />
      </div>
      <div>
        <p className="text-[12px] text-[#94A3B8]">{label}</p>
        <p className="mt-0.5 text-[15px] font-semibold text-[#0F172A]">{value}</p>
      </div>
    </div>
  );
}

function Sparkle({ size = 14, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 2l1.6 7L21 12l-7.4 3L12 22l-1.6-7L3 12l7.4-3z" />
    </svg>
  );
}
