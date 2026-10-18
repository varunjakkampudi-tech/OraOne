// Pure helpers for the platform analytics page. They only describe counts the server sent.

import type { DailyPoint } from "@/lib/api/admin-analytics";

const CHANNEL_LABELS: Record<string, string> = {
  voice: "Voice",
  chat: "Web chat",
  whatsapp: "WhatsApp",
  sms: "SMS",
  email: "Email",
  messenger: "Messenger",
  instagram: "Instagram",
  telegram: "Telegram",
  slack: "Slack",
  teams: "Teams",
  mobile: "Mobile",
  desktop: "Desktop",
};

export function channelLabel(channel: string): string {
  return CHANNEL_LABELS[channel] ?? channel;
}

export type ChannelRow = { channel: string; label: string; count: number; share: number };

/** Channel counts, largest first. ``share`` is a percentage of the total. */
export function channelRows(mix: Record<string, number>): ChannelRow[] {
  const entries = Object.entries(mix).filter(([, count]) => Number.isFinite(count) && count > 0);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);
  return entries
    .map(([channel, count]) => ({
      channel,
      label: channelLabel(channel),
      count,
      share: total ? Math.round((count / total) * 1000) / 10 : 0,
    }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}

/** Largest value in a series, never below 1 so bar heights stay defined. */
export function seriesMax(points: DailyPoint[]): number {
  return Math.max(1, ...points.map((point) => point.count));
}

export function seriesTotal(points: DailyPoint[]): number {
  return points.reduce((sum, point) => sum + point.count, 0);
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}
