import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Stethoscope, Home, GraduationCap, ShieldCheck,
  Wallet, ShoppingBag, Hotel, Car,
  ArrowRight, Users, TrendingUp, Clock, Star, Quote,
  UserCircle2, Bot, MessageCircle, Rocket,
} from "lucide-react";
import { useSEO } from "@/lib/seo";
import { BrandMark } from "@/components/marketing/Logo";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.55 },
};

const INDUSTRIES = [
  {
    slug: "healthcare",
    name: "Healthcare",
    desc: "Patient support, appointment scheduling & reminders.",
    icon: Stethoscope,
    iconBg: "#EFF6FF",
    iconColor: "#3B82F6",
    image: "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?auto=format&fit=crop&w=400&q=70",
    tag: { title: "Appointment Confirmed", sub: "Today, 10:30 AM" },
  },
  {
    slug: "real-estate",
    name: "Real Estate",
    desc: "Lead qualification, site visits & follow-ups.",
    icon: Home,
    iconBg: "#ECFDF5",
    iconColor: "#22C55E",
    image: "https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=400&q=70",
    tag: { title: "New Lead", sub: "Site Visit Request" },
  },
  {
    slug: "education",
    name: "Education",
    desc: "Admissions, inquiries and student support.",
    icon: GraduationCap,
    iconBg: "#ECFEFF",
    iconColor: "#06B6D4",
    image: "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=400&q=70",
    tag: { title: "New Inquiry", sub: "Admission Process" },
  },
  {
    slug: "insurance",
    name: "Insurance",
    desc: "Policy support, claims and renewals.",
    icon: ShieldCheck,
    iconBg: "#F3E8FF",
    iconColor: "#8B5CF6",
    image: "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?auto=format&fit=crop&w=400&q=70",
    tag: { title: "Policy Renewal", sub: "Reminder Sent" },
  },
  {
    slug: "finance",
    name: "Finance",
    desc: "Customer onboarding, KYC and support.",
    icon: Wallet,
    iconBg: "#FEF3C7",
    iconColor: "#F59E0B",
    image: "https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=400&q=70",
    tag: { title: "KYC Verified", sub: "Customer Onboarded" },
  },
  {
    slug: "retail",
    name: "Retail",
    desc: "Order tracking, returns and customer support.",
    icon: ShoppingBag,
    iconBg: "#FEE2E2",
    iconColor: "#EF4444",
    image: "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?auto=format&fit=crop&w=400&q=70",
    tag: { title: "Order Confirmed", sub: "#ORD-12345" },
  },
  {
    slug: "hospitality",
    name: "Hospitality",
    desc: "Reservations, support and guest services.",
    icon: Hotel,
    iconBg: "#FCE7F3",
    iconColor: "#EC4899",
    image: "https://images.unsplash.com/photo-1564501049412-61c2a3083791?auto=format&fit=crop&w=400&q=70",
    tag: { title: "Reservation Confirmed", sub: "Check-in: Today" },
  },
  {
    slug: "automotive",
    name: "Automotive",
    desc: "Service bookings, reminders and support.",
    icon: Car,
    iconBg: "#E0F2FE",
    iconColor: "#0EA5E9",
    image: "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?auto=format&fit=crop&w=400&q=70",
    tag: { title: "Service Reminder", sub: "Tomorrow, 11 AM" },
  },
];

const STATS = [
  { value: "15+", label: "Industries Served", icon: Users, color: "#3B82F6", bg: "#EFF6FF" },
  { value: "2.5x", label: "Higher Conversion", icon: TrendingUp, color: "#22C55E", bg: "#ECFDF5" },
  { value: "24/7", label: "AI Agent Availability", icon: Clock, color: "#8B5CF6", bg: "#F3E8FF" },
  { value: "95%", label: "Customer Satisfaction", icon: Star, color: "#F59E0B", bg: "#FEF3C7" },
];

const STEPS = [
  { icon: UserCircle2, title: "Understand Your Industry", desc: "We analyze your business and customer needs." },
  { icon: Bot, title: "Deploy AI Agents", desc: "Tailored agents trained for your industry." },
  { icon: MessageCircle, title: "Automate Conversations", desc: "Engage customers across all channels." },
  { icon: Rocket, title: "Drive Growth", desc: "Capture leads, boost conversions and scale." },
];

const TESTIMONIALS = [
  {
    quote: "OraOne helped us automate our patient appointments and reminders. We reduced no-shows by 60% and improved patient satisfaction.",
    name: "Dr. Priya Sharma",
    role: "Apollo Clinic",
    initials: "PS",
  },
  {
    quote: "Our real estate leads increased 3x in 60 days. The qualification flow is incredible — sales now focuses only on hot leads.",
    name: "Rahul Mehta",
    role: "RE/MAX India",
    initials: "RM",
  },
  {
    quote: "AI automation has been a game changer for our service bookings. Customers love the instant replies.",
    name: "Amit Verma",
    role: "Verma Motors",
    initials: "AV",
  },
];

export default function SolutionsPage() {
  useSEO({
    title: "Solutions",
    description: "AI agent solutions tailored for every industry — Healthcare, Real Estate, Education, Insurance, Finance, Retail, Hospitality and Automotive.",
  });

  const [activeT, setActiveT] = React.useState(0);

  return (
    <div className="bg-white">
      {/* ====== HERO ====== */}
      <section className="relative pt-24 pb-20 overflow-hidden bg-gradient-to-b from-[#EFF6FF] via-[#F8FAFC] to-white">
        {/* Soft decorative dots */}
        <span className="absolute top-24 left-[18%] size-2 rounded-full bg-[#22C55E]/60" />
        <span className="absolute top-32 right-[22%] size-1.5 rounded-full bg-[#3B82F6]/60" />
        <span className="absolute top-44 left-[8%] size-1 rounded-full bg-[#06B6D4]/60" />
        <span className="absolute bottom-12 right-[12%] size-1.5 rounded-full bg-[#F59E0B]/60" />
        <span className="absolute bottom-16 left-[28%] size-1 rounded-full bg-[#8B5CF6]/60" />

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.span {...fadeUp} className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-[#E2E8F0] text-xs font-bold tracking-[0.2em] text-[#2563EB] shadow-sm">
            <span className="size-1.5 rounded-full bg-[#2563EB]" />
            AI SOLUTIONS FOR EVERY INDUSTRY
          </motion.span>
          <motion.h1 {...fadeUp} className="mt-6 text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tighter text-[#0F172A]">
            Solutions for <span className="gradient-text">Every Industry</span>
          </motion.h1>
          <motion.p {...fadeUp} className="mt-5 text-[#64748B] max-w-2xl mx-auto text-base sm:text-lg leading-relaxed">
            Tailored AI solutions designed to address the unique challenges of your industry and drive meaningful results.
          </motion.p>
        </div>
      </section>

      {/* ====== INDUSTRY GRID ====== */}
      <section className="pb-20 -mt-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {INDUSTRIES.map((ind, i) => (
              <motion.div
                key={ind.slug}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.04, duration: 0.5 }}
                className="group rounded-3xl bg-white border border-[#E2E8F0] hover:border-[#2563EB]/40 hover:shadow-premium-lg transition-all overflow-hidden flex flex-col"
                data-testid={`solution-card-${ind.slug}`}
              >
                {/* Top brand panel — gradient + large ghosted industry icon
                    (replaces external stock photos: reliable, on-brand). */}
                <div className="relative h-44 overflow-hidden" style={{ background: `linear-gradient(135deg, ${ind.iconBg} 0%, #FFFFFF 100%)` }}>
                  <div className="absolute top-4 left-4 z-10 size-11 rounded-xl grid place-items-center shadow-sm" style={{ background: ind.iconBg }}>
                    <ind.icon size={20} style={{ color: ind.iconColor }} />
                  </div>
                  <ind.icon
                    className="absolute -right-4 -bottom-4 opacity-[0.12] group-hover:scale-110 transition-transform duration-500"
                    size={150}
                    style={{ color: ind.iconColor }}
                    aria-hidden="true"
                  />
                  {/* Floating notification tag */}
                  <div className="absolute bottom-3 right-3 px-3 py-1.5 rounded-xl bg-white/95 backdrop-blur shadow-md flex items-center gap-2 max-w-[80%]">
                    <div className="min-w-0">
                      <p className="text-[10px] font-bold text-[#0F172A] truncate">{ind.tag.title}</p>
                      <p className="text-[9px] text-[#64748B] truncate">{ind.tag.sub}</p>
                    </div>
                    <div className="size-5 rounded-full grid place-items-center flex-shrink-0" style={{ background: ind.iconBg }}>
                      <ind.icon size={10} style={{ color: ind.iconColor }} />
                    </div>
                  </div>
                </div>

                {/* Body */}
                <div className="p-5 flex-1 flex flex-col">
                  <h3 className="text-lg font-bold tracking-tight text-[#0F172A]">{ind.name}</h3>
                  <p className="mt-1.5 text-sm text-[#64748B] leading-relaxed flex-1">{ind.desc}</p>
                  <Link to="/signup" className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-[#2563EB] hover:gap-2 transition-all" data-testid={`solution-${ind.slug}-cta`}>
                    Learn More <ArrowRight size={14} />
                  </Link>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ====== STATS BAR ====== */}
      <section className="pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="rounded-3xl bg-[#F8FAFC] border border-[#E2E8F0] px-6 sm:px-10 py-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 divide-y md:divide-y-0 md:divide-x divide-[#E2E8F0]">
              {STATS.map((s, i) => (
                <div key={s.label} className={`flex items-center gap-4 ${i === 0 ? "" : "md:pl-6"} ${i > 1 ? "pt-6 md:pt-0" : ""}`}>
                  <div className="size-12 rounded-2xl grid place-items-center flex-shrink-0" style={{ background: s.bg }}>
                    <s.icon size={20} style={{ color: s.color }} />
                  </div>
                  <div>
                    <p className="text-3xl font-bold tracking-tighter text-[#2563EB]">{s.value}</p>
                    <p className="text-xs text-[#64748B] mt-0.5">{s.label}</p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* ====== HOW IT WORKS + TESTIMONIAL ====== */}
      <section className="pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-start">
            {/* Left: steps */}
            <motion.div {...fadeUp}>
              <p className="text-xs font-bold tracking-[0.2em] text-[#2563EB]">HOW IT WORKS</p>
              <h2 className="mt-3 text-4xl sm:text-5xl font-bold tracking-tighter text-[#0F172A] leading-tight">
                Built for Your Industry.<br />Designed for Results.
              </h2>

              <ol className="mt-10 relative">
                {/* Connector line */}
                <span className="absolute left-[19px] top-3 bottom-3 w-px bg-[#E2E8F0]" />
                {STEPS.map((s, i) => (
                  <motion.li
                    key={s.title}
                    initial={{ opacity: 0, x: -10 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.08 }}
                    className="relative flex items-start gap-5 pb-8 last:pb-0"
                  >
                    <div className="relative z-10 size-10 rounded-full bg-white border-2 border-[#2563EB] grid place-items-center flex-shrink-0">
                      <s.icon size={16} className="text-[#2563EB]" />
                    </div>
                    <div className="pt-1.5">
                      <p className="text-base font-semibold text-[#0F172A]">{s.title}</p>
                      <p className="mt-1 text-sm text-[#64748B]">{s.desc}</p>
                    </div>
                  </motion.li>
                ))}
              </ol>
            </motion.div>

            {/* Right: testimonial carousel */}
            <motion.div {...fadeUp} className="lg:mt-32">
              <div className="rounded-3xl bg-[#EFF6FF] border border-[#DBEAFE] p-8 sm:p-10">
                <Quote size={28} className="text-[#2563EB]" />
                <p className="mt-5 text-lg sm:text-xl text-[#0F172A] leading-relaxed">
                  <span className="font-semibold">OraOne helped us </span>
                  <span className="text-[#64748B]">{TESTIMONIALS[activeT].quote.replace("OraOne helped us ", "")}</span>
                </p>
                <div className="mt-8 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="size-11 rounded-full bg-gradient-to-br from-[#3B82F6] to-[#06B6D4] grid place-items-center text-white text-sm font-bold relative">
                      {TESTIMONIALS[activeT].initials}
                      <span className="absolute -bottom-0.5 -right-0.5 size-3.5 rounded-full bg-green-500 border-2 border-[#EFF6FF]" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-[#0F172A]">{TESTIMONIALS[activeT].name}</p>
                      <p className="text-xs text-[#64748B]">{TESTIMONIALS[activeT].role}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {TESTIMONIALS.map((_, i) => (
                      <button
                        key={i}
                        onClick={() => setActiveT(i)}
                        aria-label={`Testimonial ${i + 1}`}
                        data-testid={`solutions-testimonial-dot-${i}`}
                        className="group py-2 -my-2 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2563EB]/40"
                      >
                        <span className={`block h-1.5 rounded-full transition-all ${i === activeT ? "w-8 bg-[#2563EB]" : "w-1.5 bg-[#CBD5E1] group-hover:bg-[#94A3B8]"}`} />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ====== CTA ====== */}
      <section className="pb-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div {...fadeUp} className="relative rounded-3xl overflow-hidden p-8 sm:p-10 text-white" style={{ background: "linear-gradient(135deg, #2563EB 0%, #1E40AF 100%)" }}>
            <div className="absolute -top-20 -left-20 size-72 rounded-full bg-white/10" />
            <div className="absolute -bottom-32 -right-20 size-96 rounded-full bg-white/5" />
            <div className="relative grid lg:grid-cols-12 items-center gap-6">
              <div className="lg:col-span-2 flex justify-center lg:justify-start">
                <div className="size-24 rounded-full bg-white/10 grid place-items-center backdrop-blur-sm">
                  <BrandMark size={56} />
                </div>
              </div>
              <div className="lg:col-span-6">
                <h3 className="text-2xl sm:text-3xl font-bold tracking-tight">Find your industry solution today</h3>
                <p className="mt-2 text-sm text-white/80">Discover how OraOne AI agents can solve your business challenges.</p>
              </div>
              <div className="lg:col-span-4 flex flex-wrap gap-3 lg:justify-end">
                <Link to="/signup" data-testid="solutions-cta-start-free" className="px-5 py-3 rounded-xl bg-white hover:bg-white/90 text-[#2563EB] font-semibold text-sm">Start Free Beta</Link>
                <Link to="/contact" data-testid="solutions-cta-book-demo" className="px-5 py-3 rounded-xl border border-white/30 hover:bg-white/10 font-semibold text-sm">Book a Demo</Link>
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
