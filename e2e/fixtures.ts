import { test as base, expect } from "@playwright/test";

/**
 * Shared test entry point. Every spec imports `test` and `expect` from here.
 *
 * Third-party font requests are aborted, so the suites never depend on
 * external hosts. Without this, a slow or unreachable font host can delay the
 * page `load` event and make results depend on the network rather than on the
 * application.
 */
export const test = base.extend({
  context: async ({ context }, use) => {
    await context.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\//, (route) => route.abort());
    await use(context);
  },
});

export { expect };
