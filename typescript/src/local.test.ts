/**
 * The client against local memory: `membase --store DIR serve`, the same /v1 routes as the hosted
 * API answered by the membase-core engine. tests/test_typescript.py starts the server and runs
 * this file with MEMBASE_LOCAL_BASE_URL set; without it the suite is skipped.
 */
import { describe, expect, it } from "vitest";
import { Membase, NotFoundError } from "./index.js";

const base = process.env.MEMBASE_LOCAL_BASE_URL;

describe.skipIf(!base)("membase-ai against local memory", () => {
  const c = new Membase({ apiKey: "local", baseUrl: base });

  it("records a standing fact and reads it back from the profile", async () => {
    const added = await c.memories.add({ content: "Prefers dark mode", static: true });
    expect(added.status).toBe("recorded");
    const profile = await c.profile();
    expect(profile.static).toContain("Prefers dark mode");
    const { containers } = await c.containers.list();
    expect(containers).toEqual([]);   // the profile is the account's, not a container's
  });

  it("answers refusals with the same error classes", async () => {
    await expect(c.documents.get("doc_missing")).rejects.toBeInstanceOf(NotFoundError);
  });
});
