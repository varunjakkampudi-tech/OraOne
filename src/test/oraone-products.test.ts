import { describe, expect, it } from "vitest";
import { products } from "@/lib/oraone";
import { createRouter } from "@tanstack/react-router";
import { QueryClient } from "@tanstack/react-query";
import { routeTree } from "@/routeTree.gen";
import manifest from "@/lib/route-manifest.json";
describe("OraOne portfolio rules", () => {
  it("offers exactly one product in this repository: OraOne AI Chat", () => {
    expect(products).toHaveLength(1);
    expect(products.map((p) => p.name)).toEqual(["OraOne AI Chat Platform"]);
  });
  it("labels AI Chat as the current product", () => {
    expect(products[0].status).toBe("Current product");
  });
  it("keeps admin administration separate from workspace destinations", () => {
    expect(
      manifest
        .filter((r) => r.path.startsWith("/admin"))
        .every((r) => r.family === "admin" && r.role === "Platform administrator"),
    ).toBe(true);
    expect(manifest.some((r) => r.family === "workspace" && r.path.startsWith("/admin"))).toBe(
      false,
    );
  });
  it("matches every declared page including contextual deep links", () => {
    const router = createRouter({ routeTree, context: { queryClient: new QueryClient() } });
    for (const row of manifest) {
      const path = row.path.replace(/\$[A-Za-z]+/g, "sample-id");
      const matches = router.matchRoutes(path);
      expect(matches.at(-1)?.routeId, row.path).not.toBe("__root__");
      expect(matches.at(-1)?.pathname.replace(/\/$/, ""), row.path).toBe(path.replace(/\/$/, ""));
    }
  });
});
