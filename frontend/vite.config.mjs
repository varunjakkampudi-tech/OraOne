import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

const clientEnvKeys = [
  "REACT_APP_API_URL",
  "REACT_APP_BACKEND_URL",
  "REACT_APP_AUTH_PROVIDER",
  "REACT_APP_COGNITO_DOMAIN",
  "REACT_APP_COGNITO_CLIENT_ID",
  "REACT_APP_COGNITO_REDIRECT_URI",
  "REACT_APP_ORAONE_SUPPORT_WIDGET_KEY",
];

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const define = {
    "process.env.NODE_ENV": JSON.stringify(
      mode === "production" ? "production" : "development",
    ),
  };
  for (const key of clientEnvKeys) {
    define[`process.env.${key}`] = JSON.stringify(env[key] || "");
  }

  const backendTarget =
    env.REACT_APP_API_URL ||
    env.REACT_APP_BACKEND_URL ||
    "http://127.0.0.1:8000";

  return {
    plugins: [tailwindcss(), react({ include: /\.[jt]sx?$/ })],
    resolve: {
      alias: {
        "@": path.resolve(process.cwd(), "src"),
      },
    },
    define,
    esbuild: {
      loader: "jsx",
      include: /src\/.*\.[jt]sx?$/,
      exclude: [],
    },
    optimizeDeps: {
      esbuildOptions: {
        loader: {
          ".js": "jsx",
        },
      },
    },
    server: {
      port: Number(process.env.PORT) || 5173,
      strictPort: true,
      watch: {
        ignored: [
          "**/output/**",
          "**/test-results/**",
          "**/.playwright-cli/**",
          "**/build/**",
        ],
      },
      proxy: {
        "/api": {
          target: backendTarget,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: "build",
      emptyOutDir: true,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes("node_modules")) return undefined;
            if (id.includes("recharts")) return "charts";
            if (id.includes("framer-motion")) return "motion";
            return undefined;
          },
        },
      },
    },
  };
});
