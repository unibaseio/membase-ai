<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/membase-logo.png" width="72" alt="Membase">
</p>

<h1 align="center">membase-ai</h1>

<p align="center">
  <b>One memory. Every AI.</b><br>
  Drop-in memory infrastructure for AI agents and apps — the Membase SDK.
</p>

<p align="center">
  <a href="https://pypi.org/project/membase-ai/"><img src="https://img.shields.io/pypi/v/membase-ai?label=pypi" alt="PyPI"></a>
  <a href="https://www.npmjs.com/package/membase-ai"><img src="https://img.shields.io/npm/v/membase-ai?label=npm" alt="npm"></a>
  <a href="https://github.com/unibaseio/membase-ai/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT"></a>
</p>

<p align="center">
  <a href="https://www.unibase.com/memory">Website</a> ·
  <a href="https://noah-gao.gitbook.io/membase-user-guide">Docs</a> ·
  <a href="https://www.app.membase.ai">Web app</a> ·
  <a href="https://discord.gg/nB9EfPGsSf">Discord</a> ·
  <a href="https://x.com/Unibase_AI">X</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/hero.svg" width="840" alt="Sources go into one memory that every AI and app reads">
</p>

The Membase SDK: a Python client, the `membase` command line, an MCP server and a TypeScript
client. The memory lives in your Membase account or on your machine, behind the same API.

## Write once, read from any AI

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/in-action.svg" width="840" alt="Your app writes a memory; any AI reads it, here Claude Code">
</p>

Recordings: [Python SDK](https://github.com/unibaseio/membase-ai/blob/main/assets/videos/sdk.mp4) (57 s) ·
[Claude Code](https://github.com/unibaseio/membase-ai/blob/main/assets/videos/switch-ai.mp4) (1 min 33 s). The answer above is illustrative.

## Accuracy

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/results.svg" width="840" alt="LoCoMo 93.1%, LongMemEval_S 92.6%, DMR 92.2%">
</p>

On three public long-term memory benchmarks, with a few thousand tokens of context per question.

## Quickstart

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/architecture.svg" width="840" alt="Hosted, local in process, or local over HTTP">
</p>

```bash
pip install membase-ai              # hosted · Python 3.10+ · needs MEMBASE_API_KEY
pip install 'membase-ai[local]'     # local  · Python 3.12 or 3.13 · needs OPENAI_API_KEY
npm install membase-ai              # TypeScript · Node 18+
```

```python
from membase import Membase

m = Membase()                    # hosted
# m = Membase(local=True)        # local, in ~/.membase

m.memories.add("We picked Postgres for the ledger service.", container="Engineering")
m.search("what database is the ledger on?")
m.add("Design notes …", container="Engineering", custom_id="design-1")   # a document
m.ask("Which database did we choose for the ledger?")
```

Every method, its REST route and MCP tool, and the access it needs: [SDK reference](https://noah-gao.gitbook.io/membase-user-guide/build/reference/sdk-quickstart).
The package is `membase-ai`; `membase` on PyPI is unrelated.

## Command line

```bash
membase --local add "We picked Postgres for the ledger" --container Engineering
membase --local search "what did we pick for the ledger?"
membase --local ask "Which database is the ledger on?"
membase --local import ~/Downloads/claude-export.json     # Claude, ChatGPT, markdown or JSON chats
membase --local agent ingest trace.json --agent coder
membase --local agent search "fix flaky deploy" --agent coder
```

Without `--local` (or `--store DIR`, both before the command) commands use the hosted API; `agent`,
`import` and `serve` need `membase-ai[local]`.

## MCP

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/mcp.svg" width="840" alt="MCP clients, hosted or local server, same tools">
</p>

```bash
claude mcp add membase -- membase --local mcp                                   # local
claude mcp add --transport http membase https://api.app.membase.io/mcp-http \
  --header "Authorization: Bearer $MEMBASE_API_KEY"                             # hosted
```

Hosted without the header, the connection signs you in and is read-only. Setup for Claude, ChatGPT,
Cursor, Codex and other clients: [Connect your AI](https://noah-gao.gitbook.io/membase-user-guide/connect).

## Docs

- [SDK reference](https://noah-gao.gitbook.io/membase-user-guide/build/reference/sdk-quickstart): methods, REST routes, MCP tools, access levels
- [Memory operations](https://noah-gao.gitbook.io/membase-user-guide/build/guides/memory-operations): containers, documents, memories, profile, ask
- [Authentication](https://noah-gao.gitbook.io/membase-user-guide/build/reference/authentication): keys and what each one can reach
- [Connect your AI](https://noah-gao.gitbook.io/membase-user-guide/connect): per-client MCP setup
- [Local engine](https://github.com/unibaseio/membase-ai/blob/main/docs/reference.md): what it stores, `membase serve`, settings

## License

MIT. `membase-ai[local]` also installs membase-core, the compiled engine, under Unibase's
proprietary license.
