import { apiRequest } from "./client";

// Billing and usage belong to the organization. Plan changes (checkout) and the
// customer portal are not wired to the studio yet; this module only reads.

export type Plan = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  price_cents: number;
  price_cents_yearly: number;
  currency: string;
  features: unknown[];
  limits: Record<string, unknown>;
  is_active: boolean;
  sort_order: number;
};

export type PlanList = { items: Plan[]; total: number };

export type Subscription = {
  id: string;
  organization_id: string;
  plan_id: string;
  status: string;
  billing_cycle: string;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  created_at: string;
  plan: Plan;
};

export type UsageMetric = {
  metric: string;
  label: string;
  category: "resource" | "metered" | string;
  used: number;
  limit: number;
  unlimited: boolean;
  percent: number;
  period: string | null;
};

export type UsageSnapshot = {
  plan_code: string;
  plan_name: string;
  metrics: UsageMetric[];
  generated_at: string;
};

export function listPlans() {
  return apiRequest<PlanList>("/billing/plans");
}

export function getSubscription() {
  return apiRequest<Subscription>("/billing/subscription");
}

export function getUsage() {
  return apiRequest<UsageSnapshot>("/usage");
}
