import type { ComponentType } from "react";
import {
  Bot,
  BarChart3,
  BookOpen,
  Building2,
  CalendarCheck,
  Code2,
  FlaskConical,
  Home,
  Hammer,
  Inbox,
  Layers,
  MessageCircle,
  MessageSquare,
  Orbit,
  Phone,
  Plug,
  Reply,
  Scale,
  ShoppingBag,
  Smartphone,
  Sparkles,
  Store,
  Stethoscope,
  Upload,
  Users,
  Wand2,
  Workflow,
  Wrench,
  Dumbbell,
  Globe,
  MessageSquareText,
} from "lucide-react";

type Icon = ComponentType<{ className?: string; "aria-hidden"?: boolean }>;

// Icons are chosen by meaning, so each card reads at a glance. Keys match the content.

const USE_CASE_ICON: Record<string, Icon> = {
  "Dental clinic": Stethoscope,
  "Plumbing and heating": Wrench,
  "Fitness studio": Dumbbell,
  "Online shop": ShoppingBag,
  "Accountancy or law practice": Scale,
  "Letting agency": Home,
};

const PRODUCT_ICON: Record<number, Icon> = {
  1: Bot,
  2: Phone,
  3: MessageCircle,
  4: Layers,
  5: Workflow,
  6: Wand2,
  7: Store,
  8: Smartphone,
  9: Building2,
  10: Orbit,
};

const STEP_ICON: Icon[] = [Upload, MessageSquareText, Globe];

/** Picks an icon for a capability from its title. Falls back to a sparkle. */
export function capabilityIcon(title: string): Icon {
  const t = title.toLowerCase();
  if (t.includes("widget")) return Code2;
  if (t.includes("inbox") && t.includes("lead")) return Inbox;
  if (t.includes("inbox")) return Inbox;
  if (t.includes("staff") || t.includes("reply")) return Reply;
  if (t.includes("knowledge") || t.includes("document")) return BookOpen;
  if (t.includes("answer")) return MessageSquare;
  if (t.includes("lead")) return Users;
  if (t.includes("analytics")) return BarChart3;
  if (t.includes("api") || t.includes("webhook")) return Plug;
  if (t.includes("playground") || t.includes("test")) return FlaskConical;
  if (t.includes("team")) return Users;
  if (t.includes("assistant")) return Bot;
  if (t.includes("phone") || t.includes("call")) return Phone;
  if (t.includes("whatsapp")) return MessageCircle;
  if (t.includes("meeting")) return CalendarCheck;
  if (t.includes("setup") || t.includes("simple")) return Hammer;
  return Sparkles;
}

export function industryIcon(industry: string): Icon {
  return USE_CASE_ICON[industry] ?? Sparkles;
}

export function productIcon(id: number): Icon {
  return PRODUCT_ICON[id] ?? Layers;
}

export function stepIcon(index: number): Icon {
  return STEP_ICON[index] ?? Sparkles;
}
