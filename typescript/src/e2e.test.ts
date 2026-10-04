/**
 * The client against a live Membase server. membase-platform's tests/test_sdk_e2e.py boots the hosted app with the
 * fake VM and a fake agent, mints a developer key at Read & write over one container, and runs
 * this file with:
 *
 *   MEMBASE_TEST_BASE_URL   the server
 *   MEMBASE_TEST_KEY        the key's token
 *   MEMBASE_TEST_CONTAINER  the container it reaches
 *   MEMBASE_TEST_OTHER      a container it does not
 */
import { describe, expect, it } from "vitest";
import { Membase, PermissionDeniedError, NotFoundError, UnprocessableEntityError } from "./index.js";

const base = process.env.MEMBASE_TEST_BASE_URL!;
const key = process.env.MEMBASE_TEST_KEY!;
const container = process.env.MEMBASE_TEST_CONTAINER!;
const other = process.env.MEMBASE_TEST_OTHER!;

describe("membase-ai against a live server", () => {
  const c = new Membase({ apiKey: key, baseUrl: base });

  it("sees only the containers in reach", async () => {
    const { containers } = await c.containers.list();
    expect(containers.map((x) => x.id)).toEqual([container]);
  });

  it("adds a document, lists it, reads it", async () => {
    const added = await c.add({ container, content: "hello from typescript", customId: "ts-1", title: "TS" });
    expect(added.status).toBe("queued");
    expect(added.container).toBe(container);
    const again = await c.add({ container, content: "hello from typescript", customId: "ts-1" });
    expect(["exists", "queued"]).toContain(again.status);
    const docs = await c.documents.list({ container });
    expect(docs.documents.length).toBeGreaterThan(0);
    const one = await c.documents.get(docs.documents[0].id);
    expect(one.container).toBe(container);
  });

  it("searches and reads the profile", async () => {
    const hits = await c.search({ q: "pricing", limit: 3 });
    expect(hits.results.length).toBeGreaterThan(0);
    expect(hits.results[0].container).toBe(container);
    const p = await c.profile();
    expect(p).toHaveProperty("static");
  });

  it("saves a memory, and reports honestly when a static fact was not recorded", async () => {
    const out = await c.memories.add({ content: "We settled on Postgres.", container });
    expect(out).toBeTruthy();
    // The fake agent never writes the profile, so the platform refuses to call the fact recorded.
    await expect(c.memories.add({ content: "The user prefers dark mode.", static: true })).rejects.toBeInstanceOf(UnprocessableEntityError);
  });

  it("is refused outside its reach, above its level, and on unknown ids", async () => {
    await expect(c.search({ q: "x", container: other })).rejects.toBeInstanceOf(PermissionDeniedError);
    const docs = await c.documents.list({ container });
    // Read & write cannot delete: the verb is above the key's level.
    await expect(c.documents.delete(docs.documents[0].id, { confirm: true })).rejects.toBeInstanceOf(PermissionDeniedError);
    await expect(c.documents.get("srcitem_does_not_exist")).rejects.toBeInstanceOf(NotFoundError);
    // An unknown, expired or revoked key is refused as 403 `unauthorized`; a missing bearer is the 401.
    const bad = new Membase({ apiKey: "mbk_nope", baseUrl: base, maxRetries: 0 });
    const e = await bad.containers.list().catch((x) => x);
    expect(e).toBeInstanceOf(PermissionDeniedError);
    expect(e.code).toBe("unauthorized");
    const res = await fetch(base + "/v1/containers");
    expect(res.status).toBe(401);
  });
});
