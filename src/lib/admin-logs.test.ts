import { describe, expect, it } from "vitest";
import {
  DEFAULT_LOG_FILTERS,
  EXPORT_ROW_CAP,
  LIST_PAGE_SIZE,
  buildFilterParams,
  downloadNotice,
  downloadQuery,
  errorListQuery,
  formatDuration,
  hasActiveFilters,
  hasNextPage,
  pageCount,
  rangeBounds,
  requestIdProblem,
  type LogFilters,
} from "@/lib/admin-logs";

const NOW = new Date("2026-10-18T12:00:00.000Z");

function filters(overrides: Partial<LogFilters>): LogFilters {
  return { ...DEFAULT_LOG_FILTERS, ...overrides };
}

describe("rangeBounds", () => {
  it("ends at now and starts one preset window earlier", () => {
    expect(rangeBounds("1h", NOW)).toEqual({
      start: "2026-10-18T11:00:00.000Z",
      end: "2026-10-18T12:00:00.000Z",
    });
    expect(rangeBounds("24h", NOW).start).toBe("2026-10-17T12:00:00.000Z");
    expect(rangeBounds("7d", NOW).start).toBe("2026-10-11T12:00:00.000Z");
    expect(rangeBounds("30d", NOW).start).toBe("2026-09-18T12:00:00.000Z");
  });

  it("does not mutate the clock value it is given", () => {
    const clock = new Date(NOW.getTime());
    rangeBounds("7d", clock);
    expect(clock.getTime()).toBe(NOW.getTime());
  });
});

describe("requestIdProblem", () => {
  it("accepts blank input and well-formed IDs", () => {
    expect(requestIdProblem("")).toBeNull();
    expect(requestIdProblem("   ")).toBeNull();
    expect(requestIdProblem("req-7f3a9c10")).toBeNull();
    expect(requestIdProblem("  0b6c1d2e-3f4a-4b5c-8d9e-0f1a2b3c4d5e  ")).toBeNull();
  });

  it("rejects short IDs and anything that could inject markup or separators", () => {
    expect(requestIdProblem("abc")).not.toBeNull();
    expect(requestIdProblem("req id with spaces")).not.toBeNull();
    expect(requestIdProblem("req/../../etc")).not.toBeNull();
    expect(requestIdProblem("<script>alert(1)</script>")).not.toBeNull();
    expect(requestIdProblem("a".repeat(129))).not.toBeNull();
  });
});

describe("buildFilterParams", () => {
  it("sends only the filters that are set", () => {
    const params = buildFilterParams(DEFAULT_LOG_FILTERS, NOW);
    expect([...params.keys()].sort()).toEqual(["end", "start"]);
  });

  it("trims the route and converts the status to a number", () => {
    const params = buildFilterParams(filters({ route: "  /api/admin/logs  ", status: "503" }), NOW);
    expect(params.get("route")).toBe("/api/admin/logs");
    expect(params.get("status")).toBe("503");
  });

  it("drops a request ID that the server would reject", () => {
    const params = buildFilterParams(filters({ requestId: "bad id" }), NOW);
    expect(params.has("request_id")).toBe(false);
  });

  it("keeps a valid request ID, trimmed", () => {
    const params = buildFilterParams(filters({ requestId: " req-7f3a9c10 " }), NOW);
    expect(params.get("request_id")).toBe("req-7f3a9c10");
  });
});

describe("errorListQuery and downloadQuery", () => {
  it("pages the list by fixed-size offsets", () => {
    const first = new URLSearchParams(errorListQuery(DEFAULT_LOG_FILTERS, NOW, 0));
    const third = new URLSearchParams(errorListQuery(DEFAULT_LOG_FILTERS, NOW, 2));
    expect(first.get("limit")).toBe(String(LIST_PAGE_SIZE));
    expect(first.get("offset")).toBe("0");
    expect(third.get("offset")).toBe(String(2 * LIST_PAGE_SIZE));
  });

  it("never sends a negative offset", () => {
    expect(new URLSearchParams(errorListQuery(DEFAULT_LOG_FILTERS, NOW, -3)).get("offset")).toBe(
      "0",
    );
  });

  it("asks for the requested format and no paging", () => {
    const params = new URLSearchParams(downloadQuery(DEFAULT_LOG_FILTERS, NOW, "csv"));
    expect(params.get("format")).toBe("csv");
    expect(params.has("limit")).toBe(false);
    expect(params.has("offset")).toBe(false);
  });
});

describe("filter state", () => {
  it("detects when any filter departs from the default", () => {
    expect(hasActiveFilters(DEFAULT_LOG_FILTERS)).toBe(false);
    expect(hasActiveFilters(filters({ route: "  " }))).toBe(false);
    expect(hasActiveFilters(filters({ route: "/api" }))).toBe(true);
    expect(hasActiveFilters(filters({ status: "500" }))).toBe(true);
    expect(hasActiveFilters(filters({ range: "7d" }))).toBe(true);
    expect(hasActiveFilters(filters({ requestId: "req-7f3a9c10" }))).toBe(true);
  });
});

describe("paging", () => {
  it("counts pages with at least one page for an empty result", () => {
    expect(pageCount(0)).toBe(1);
    expect(pageCount(50)).toBe(1);
    expect(pageCount(51)).toBe(2);
  });

  it("reports whether another page follows", () => {
    expect(hasNextPage(120, 0)).toBe(true);
    expect(hasNextPage(120, 2)).toBe(false);
    expect(hasNextPage(50, 0)).toBe(false);
  });
});

describe("display helpers", () => {
  it("formats durations in milliseconds or seconds", () => {
    expect(formatDuration(42.4)).toBe("42 ms");
    expect(formatDuration(1500)).toBe("1.5 s");
    expect(formatDuration(-1)).toBe("not recorded");
    expect(formatDuration(Number.NaN)).toBe("not recorded");
  });

  it("explains a truncated download in plain words", () => {
    expect(downloadNotice("json", false)).toBe("Downloaded JSON.");
    const truncated = downloadNotice("csv", true);
    expect(truncated).toContain(EXPORT_ROW_CAP.toLocaleString("en-US"));
    expect(truncated).toContain("Narrow the time range");
  });
});
