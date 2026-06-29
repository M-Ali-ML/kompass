import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = defineConfig([
  ...nextVitals,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    // Isolated Next build dir used by the Playwright E2E webServer.
    ".next-e2e/**",
    // Isolated Next build dir used by `npm run dev`.
    ".next-dev/**",
    // Playwright output (HTML report + trace bundles) and test artifacts.
    "playwright-report/**",
    "test-results/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
