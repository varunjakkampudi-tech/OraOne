// The shared Lovable/TanStack Start config already provides the framework plugins,
// the "@" path alias, environment injection and the nitro build. Do not add those
// plugins again here; extend the configuration only through the `vite` and
// `tanstackStart` options below.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

/** Backend origin used by the development server and the preview server. */
const apiTarget = process.env["API_PROXY_TARGET"] ?? "http://localhost:8000";

/**
 * Same-origin `/api` proxy. The browser always talks to the web origin, so
 * session cookies behave in development, preview and production alike.
 */
const apiProxy = {
  "/api": {
    target: apiTarget,
    changeOrigin: false,
  },
};

export default defineConfig({
  tanstackStart: {
    // Use src/server.ts (our SSR error wrapper) as the server entry point.
    server: { entry: "server" },
  },
  vite: {
    server: { proxy: apiProxy },
    preview: { proxy: apiProxy },
  },
});
