import { defineConfig } from "vitest/config";

// Unit tests live in tests/unit and run in a plain Node environment (the pure
// lib/ helpers need no DOM). Playwright's tests/e2e/*.spec.js are excluded so
// the two runners never pick up each other's files.
export default defineConfig({
  test: {
    include: ["tests/unit/**/*.test.js"],
    environment: "node",
  },
});
