/** The client against a scripted `fetch`: request shapes, error classes, retries. */
import { describe, expect, it } from "vitest";
import { Membase, PermissionDeniedError, RateLimitError, NotFoundError, AuthenticationError, APIConnectionError } from "./index.js";

type Call = { url: URL; init: RequestInit };

function scripted(responses: Array<{ status: number; body?: unknown; headers?: Record<string, string> }>) {
  const calls: Call[] = [];
  const fetchImpl = (async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: new URL(String(input)), init: init ?? {} });
    const next = responses.shift();
    if (!next) throw new Error("no scripted response left");
    return new Response(next.body === undefined ? null : JSON.stringify(next.body), {
      status: next.status,
      headers: { "content-type": "application/json", ...(next.headers ?? {}) },
    });
  }) as typeof fetch;
  return { calls, fetchImpl };
}

describe("Membase", () => {
  it("needs a key", () => {
    const saved = process.env.MEMBASE_API_KEY;
    delete process.env.MEMBASE_API_KEY;
    try {
      expect(() => new Membase()).toThrow(/MEMBASE_API_KEY/);
    } finally {
      if (saved !== undefined) process.env.MEMBASE_API_KEY = saved;
    }
  });

  it("sends the protocol's shapes with the bearer", async () => {
    const { calls, fetchImpl } = scripted([
      { status: 202, body: { document_id: "srcitem_1", container: "mv-1", status: "queued" } },
      { status: 200, body: { query: "q", results: [], containers: [] } },
      { status: 200, body: { static: [], dynamic: [] } },
      { status: 200, body: { containers: [] } },
      { status: 200, body: { documents: [] } },
      { status: 200, body: { status: "confirmation_required", verb: "delete_document", how: "…" } },
      { status: 202, body: { status: "queued" } },
    ]);
    const c = new Membase({ apiKey: "mbk_test", baseUrl: "https://api.example.test/", fetch: fetchImpl, maxRetries: 0 });

    const added = await c.add({ container: "mv-1", content: "hello", customId: "d1", metadata: { k: "v" } });
    expect(added.document_id).toBe("srcitem_1");
    expect(calls[0].url.toString()).toBe("https://api.example.test/v1/documents");
    expect(calls[0].init.method).toBe("POST");
    expect((calls[0].init.headers as Record<string, string>).Authorization).toBe("Bearer mbk_test");
    expect(JSON.parse(String(calls[0].init.body))).toEqual({ container: "mv-1", content: "hello", title: "", metadata: { k: "v" }, custom_id: "d1" });

    await c.search({ q: "q", container: "mv-1", limit: 5 });
    expect(JSON.parse(String(calls[1].init.body))).toEqual({ q: "q", container: "mv-1", limit: 5 });

    await c.profile({ q: "hours" });
    expect(calls[2].url.pathname + calls[2].url.search).toBe("/v1/profile?q=hours");

    await c.containers.list();
    expect(calls[3].url.pathname).toBe("/v1/containers");

    await c.documents.list({ container: "mv-1" });
    expect(calls[4].url.search).toBe("?container=mv-1");

    const refused = await c.documents.delete("srcitem_1");
    expect(refused.status).toBe("confirmation_required");
    expect(calls[5].init.method).toBe("DELETE");
    expect(calls[5].url.search).toBe("?confirm=false");

    await c.memories.add({ content: "dark mode", static: true });
    expect(JSON.parse(String(calls[6].init.body))).toEqual({ content: "dark mode", static: true, title: "" });
  });

  it("maps statuses to error classes and keeps the envelope", async () => {
    const env = (code: string, message: string) => ({ error: { code, message, details: {}, retryable: false, trace_id: "t-1" } });
    const { fetchImpl } = scripted([
      { status: 403, body: env("unauthorized", "may not use that container") },
      { status: 404, body: env("not_found", "no such document") },
      { status: 401, body: env("unauthenticated", "missing credential") },
    ]);
    const c = new Membase({ apiKey: "mbk_test", baseUrl: "https://api.example.test", fetch: fetchImpl, maxRetries: 0 });
    const e = await c.search({ q: "x", container: "mv-2" }).catch((x) => x);
    expect(e).toBeInstanceOf(PermissionDeniedError);
    expect(e.code).toBe("unauthorized");
    expect(e.traceId).toBe("t-1");
    expect(e.status).toBe(403);
    await expect(c.documents.get("nope")).rejects.toBeInstanceOf(NotFoundError);
    await expect(c.containers.list()).rejects.toBeInstanceOf(AuthenticationError);
  });

  it("retries 429 and 5xx, then gives up with the last answer", async () => {
    const { calls, fetchImpl } = scripted([
      { status: 429, body: { error: { code: "rate_limited", message: "budget" } }, headers: { "Retry-After": "0" } },
      { status: 503, body: { error: { code: "provider_unavailable", message: "down" } } },
      { status: 200, body: { containers: [{ id: "mv-1", name: "A" }] } },
    ]);
    const c = new Membase({ apiKey: "mbk_test", baseUrl: "https://api.example.test", fetch: fetchImpl, maxRetries: 2 });
    const out = await c.containers.list();
    expect(out.containers[0].id).toBe("mv-1");
    expect(calls.length).toBe(3);

    const exhausted = scripted([
      { status: 429, body: { error: { code: "rate_limited", message: "budget" } }, headers: { "Retry-After": "0" } },
      { status: 429, body: { error: { code: "rate_limited", message: "budget" } }, headers: { "Retry-After": "0" } },
    ]);
    const c2 = new Membase({ apiKey: "mbk_test", baseUrl: "https://api.example.test", fetch: exhausted.fetchImpl, maxRetries: 1 });
    await expect(c2.containers.list()).rejects.toBeInstanceOf(RateLimitError);
    expect(exhausted.calls.length).toBe(2);
  });

  it("turns a dead connection into APIConnectionError", async () => {
    const failing = (async () => {
      throw new TypeError("fetch failed");
    }) as unknown as typeof fetch;
    const c = new Membase({ apiKey: "mbk_test", baseUrl: "https://api.example.test", fetch: failing, maxRetries: 0 });
    await expect(c.containers.list()).rejects.toBeInstanceOf(APIConnectionError);
  });
});
