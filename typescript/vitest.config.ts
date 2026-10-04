import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    // The e2e file only runs when tests/test_sdk_e2e.py points it at a live server.
    exclude: process.env.MEMBASE_TEST_BASE_URL ? [] : ["src/e2e.test.ts", "node_modules/**"],
  },
});
