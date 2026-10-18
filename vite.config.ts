import { fileURLToPath, URL } from "node:url";
import { defineConfig, loadEnv } from "vite";
import tailwindcss from "@tailwindcss/vite";
import tsConfigPaths from "vite-tsconfig-paths";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import { nitro } from "nitro/vite";
import viteReact from "@vitejs/plugin-react";

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

const srcDir = fileURLToPath(new URL("./src", import.meta.url));

export default defineConfig(({ command, mode }) => {
  // Expose only VITE_* variables to client code, as import.meta.env.<NAME>.
  const envDefine = Object.fromEntries(
    Object.entries(loadEnv(mode, process.cwd(), "VITE_")).map(([key, value]) => [
      `import.meta.env.${key}`,
      JSON.stringify(value),
    ]),
  );

  return {
    define: envDefine,
    resolve: {
      alias: { "@": srcDir },
      dedupe: [
        "react",
        "react-dom",
        "react/jsx-runtime",
        "react/jsx-dev-runtime",
        "@tanstack/react-query",
        "@tanstack/query-core",
      ],
    },
    optimizeDeps: {
      include: [
        "react",
        "react-dom",
        "react-dom/client",
        "react/jsx-runtime",
        "react/jsx-dev-runtime",
      ],
    },
    plugins: [
      tailwindcss(),
      tsConfigPaths({ projects: ["./tsconfig.json"] }),
      // src/server.ts is the SSR error wrapper and the server entry point.
      tanstackStart({
        importProtection: {
          behavior: "error",
          client: {
            files: ["**/server/**"],
            specifiers: ["server-only"],
          },
        },
        server: { entry: "server" },
      }),
      // The production preset comes from NITRO_PRESET (frontend.Dockerfile sets node-server).
      ...(command === "build" ? [nitro()] : []),
      viteReact(),
    ],
    server: { proxy: apiProxy },
    preview: { proxy: apiProxy },
  };
});
