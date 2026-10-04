# membase-ai

Membase — long-term memory for AI. The TypeScript client for the [Membase](https://membase.ai) API, hosted or local.

```bash
npm install membase-ai
export MEMBASE_API_KEY="mbk_…"     # Connect › Developer keys in the Membase app
```

```ts
import { Membase } from "membase-ai";

const client = new Membase();

await client.add({ container: "mv-…", content: "Call notes with Acme: they want SSO before the pilot.", customId: "call-2026-09-24" });
const { results } = await client.search({ q: "what does Acme need before the pilot", limit: 5 });
console.log(results[0].content);

await client.profile({ q: "working hours" });        // who the user is (needs the profile tick on the key)
await client.containers.list();
await client.documents.list({ container: "mv-…" });
await client.memories.add({ content: "The user prefers dark mode.", static: true });
await client.documents.delete("srcitem_…", { confirm: true });   // Full access; confirm means the person agreed
```

Every method is one operation of the Membase agent protocol; access level, reach and confirmation
rules are enforced server-side. Errors are one class per HTTP status (`PermissionDeniedError`,
`RateLimitError`, …) and carry the API's `code` and `traceId`. 429 and 5xx answers are retried
twice with backoff; the default timeout is 90 s, because the first search after a quiet spell
waits for the user's memory to wake.

Node 18+ (global `fetch`), Deno and Bun. Zero dependencies. Works against a self-hosted Membase
too: `new Membase({ baseUrl: "http://localhost:8080" })`.

## Local memory

Run the engine on your machine with the Python package and point the client at it — same
methods, same answers:

```bash
pip install 'membase-ai[local]'
membase --local serve            # http://127.0.0.1:8787/v1, store under ~/.membase
```

```ts
const local = new Membase({ apiKey: "local", baseUrl: "http://127.0.0.1:8787" });
```

`membase-sdk` on npm is the earlier name of this package and keeps working as an alias.
