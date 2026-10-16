// ESLint flat configuration for the web application.
//
// Rules:
//   * JavaScript and TypeScript recommended sets
//   * React Hooks rules (hook order and dependencies)
//   * Fast Refresh boundaries, so components hot-reload safely
//   * Prettier is enforced as a lint rule, so formatting drift is reported here
//
// The backend is Python and is linted by Ruff (see backend/pyproject.toml).
import js from "@eslint/js";
import eslintPluginPrettier from "eslint-plugin-prettier/recommended";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "dist",
      ".output",
      ".vinxi",
      ".wrangler",
      "backend/**",
      "node_modules/**",
      "playwright-report/**",
      "test-results/**",
      "src/routeTree.gen.ts",
    ],
  },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "no-restricted-imports": [
        "error",
        {
          paths: [
            {
              name: "server-only",
              message:
                "TanStack Start does not use the Next.js `server-only` package. Rename the module to `*.server.ts` or mark it with `@tanstack/react-start/server-only`.",
            },
          ],
        },
      ],
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      // Unused variables are caught by the TypeScript compiler (noUnusedLocals is not
      // enabled), so ESLint leaves them alone to avoid duplicate reports.
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
  {
    // shadcn/ui primitives export component variants next to the components by design.
    files: ["src/components/ui/**/*.{ts,tsx}"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
  {
    // End-to-end tests run in Node and use Playwright's fixtures.
    files: ["e2e/**/*.ts", "playwright.config.ts"],
    rules: {
      "react-hooks/rules-of-hooks": "off",
    },
  },
  eslintPluginPrettier,
);
