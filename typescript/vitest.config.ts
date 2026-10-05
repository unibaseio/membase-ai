import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    exclude: process.env.MEMBASE_TEST_BASE_URL ? [] : ["src/e2e.test.ts", "node_modules/**"],
  },
});
