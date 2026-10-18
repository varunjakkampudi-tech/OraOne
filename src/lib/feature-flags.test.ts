import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const getEnabledFeatureFlags = vi.fn();

vi.mock("@/lib/api/feature-flags", () => ({
  getEnabledFeatureFlags: (...args: unknown[]) => getEnabledFeatureFlags(...args),
}));

import {
  flagKeysFrom,
  isFlagEnabled,
  resetFeatureFlagCache,
  useFeatureFlag,
} from "@/lib/feature-flags";

describe("feature flag hook", () => {
  beforeEach(() => {
    getEnabledFeatureFlags.mockReset();
    resetFeatureFlagCache();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("is off when the call fails", async () => {
    getEnabledFeatureFlags.mockRejectedValue(new Error("network down"));
    const { result } = renderHook(() => useFeatureFlag("admin_analytics_console"));
    expect(result.current).toBe(false);
    await waitFor(() => expect(getEnabledFeatureFlags).toHaveBeenCalledTimes(1));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(result.current).toBe(false);
  });

  it("is off when the response is malformed", async () => {
    getEnabledFeatureFlags.mockResolvedValue({ enabled: "admin_analytics_console" });
    const { result } = renderHook(() => useFeatureFlag("admin_analytics_console"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(result.current).toBe(false);
  });

  it("is off when the flag is not in the enabled list", async () => {
    getEnabledFeatureFlags.mockResolvedValue({
      enabled: ["org_analytics_summary"],
      cache_ttl_seconds: 60,
    });
    const { result } = renderHook(() => useFeatureFlag("admin_analytics_console"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(result.current).toBe(false);
  });

  it("turns on only when the server lists the flag", async () => {
    getEnabledFeatureFlags.mockResolvedValue({
      enabled: ["admin_analytics_console"],
      cache_ttl_seconds: 60,
    });
    const { result } = renderHook(() => useFeatureFlag("admin_analytics_console"));
    await waitFor(() => expect(result.current).toBe(true));
  });

  it("does not cache a failed call, so the next render asks again", async () => {
    getEnabledFeatureFlags.mockRejectedValueOnce(new Error("boom"));
    getEnabledFeatureFlags.mockResolvedValueOnce({ enabled: ["admin_analytics_console"] });
    const first = renderHook(() => useFeatureFlag("admin_analytics_console"));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(first.result.current).toBe(false);
    first.unmount();

    const second = renderHook(() => useFeatureFlag("admin_analytics_console"));
    await waitFor(() => expect(second.result.current).toBe(true));
    expect(getEnabledFeatureFlags).toHaveBeenCalledTimes(2);
  });
});

describe("flag helpers", () => {
  it("reads only string keys from the enabled list", () => {
    const keys = flagKeysFrom({ enabled: ["a", 3, null, "b"] });
    expect([...keys].sort()).toEqual(["a", "b"]);
  });

  it("returns no flags for anything unexpected", () => {
    expect(flagKeysFrom(undefined).size).toBe(0);
    expect(flagKeysFrom({}).size).toBe(0);
    expect(flagKeysFrom("enabled").size).toBe(0);
  });

  it("checks membership", () => {
    expect(isFlagEnabled(new Set(["x"]), "x")).toBe(true);
    expect(isFlagEnabled(new Set(["x"]), "y")).toBe(false);
  });
});
