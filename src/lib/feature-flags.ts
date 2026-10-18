// Client view of beta feature flags. The server decides every flag; this module only asks
// for the list and reads it. A failed or malformed call means every flag is off.

import { useEffect, useState } from "react";
import { getEnabledFeatureFlags } from "@/lib/api/feature-flags";

export const FLAG_CACHE_MS = 60_000;

let cache: { at: number; keys: Promise<ReadonlySet<string>> } | null = null;

/** Reads the ``enabled`` list from a response. Anything unexpected yields no flags. */
export function flagKeysFrom(response: unknown): ReadonlySet<string> {
  const enabled = (response as { enabled?: unknown } | null | undefined)?.enabled;
  if (!Array.isArray(enabled)) return new Set();
  return new Set(enabled.filter((key): key is string => typeof key === "string"));
}

export function isFlagEnabled(keys: ReadonlySet<string>, key: string): boolean {
  return keys.has(key);
}

/** Loads the enabled keys once per 60 seconds. A failed call is not cached. */
export function loadFeatureFlagKeys(now: number = Date.now()): Promise<ReadonlySet<string>> {
  if (cache && now - cache.at < FLAG_CACHE_MS) return cache.keys;
  const keys = getEnabledFeatureFlags().then(
    (response) => flagKeysFrom(response),
    () => {
      cache = null;
      return new Set<string>();
    },
  );
  cache = { at: now, keys };
  return keys;
}

export function resetFeatureFlagCache(): void {
  cache = null;
}

/** True only when the server has confirmed the flag is on for this caller. Off by default. */
export function useFeatureFlag(key: string): boolean {
  const [enabled, setEnabled] = useState(false);
  useEffect(() => {
    let active = true;
    void loadFeatureFlagKeys().then((keys) => {
      if (active) setEnabled(isFlagEnabled(keys, key));
    });
    return () => {
      active = false;
    };
  }, [key]);
  return enabled;
}
