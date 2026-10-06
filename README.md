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
  <a href="https://unibaseio.gitbook.io/unibase-docs/membase">Docs</a> ·
  <a href="https://www.app.membase.ai">Web app</a> ·
  <a href="https://discord.gg/nB9EfPGsSf">Discord</a> ·
  <a href="https://x.com/Unibase_AI">X</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/every-ai.svg" width="840" alt="Every AI, same memory: the assistant and Claude Code answer from one memory">
</p>

Membase gives agents and apps context that persists, built for production. This repository is its
SDK for developers: the Python client, the `membase` command line, an MCP server and the
TypeScript client, for memory hosted in your Membase account or kept on your machine.
[Unibase Memory](https://www.unibase.com/memory), the product for people (the
[Chrome extension](https://chromewebstore.google.com/detail/unibase-memory/edmncknbiihfoakimejbepnaeemaaamf)
([video guide](https://www.youtube.com/watch?v=c_dZHJXnxlc)), the web app and the desktop app), is
powered by Membase.

## How it works

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/hero.svg" width="840" alt="Sources go into one memory that every AI and app reads">
</p>

1. **Install** the SDK: `pip install membase-ai` or `npm install membase-ai`.
2. **Integrate**: connect any MCP-compatible agent with one command (see [MCP](#mcp)), or call the
   client from your code.
3. **Manage**: search, edit and organise what the memory holds from the
   [web app](https://www.app.membase.ai), or with `membase` on the command line.
4. **Retrieve**: your agent pulls the relevant context for every request (`search`), or asks the
   memory for an answer (`ask`).

## See it in action

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/sdk-card.svg" alt="Python SDK: add a memory, search it"><br>
      <b>From your code</b>: <code>memories.add()</code> writes, <code>search()</code> returns passages,
      each naming the memory it came from. <a href="https://github.com/unibaseio/membase-ai/blob/main/assets/videos/sdk.mp4">Watch the recording (57 s)</a>
    </td>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/mcp-card.svg" alt="Claude Code reads the memory over MCP"><br>
      <b>From any AI</b>: one <code>claude mcp add</code> connects Claude Code to the same memory.
      <a href="https://github.com/unibaseio/membase-ai/blob/main/assets/videos/switch-ai.mp4">Watch the recording (1 min 33 s)</a>
    </td>
  </tr>
</table>

The outputs shown are illustrative.

## Benchmarks

Accuracy and context efficiency of the engine, measured end to end with membase-bench:

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/results.svg" width="840" alt="LoCoMo 93.1%, LongMemEval_S 92.6%, DMR 92.2%">
</p>

## Install

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/architecture.svg" width="840" alt="The Membase client: hosted API or local engine">
</p>

| | `pip install membase-ai` | `pip install 'membase-ai[local]'` |
|---|---|---|
| Memory lives | in your Membase account (hosted) | on this machine, under `~/.membase` |
| You need | an API key (`MEMBASE_API_KEY`) | `OPENAI_API_KEY` (see [Local settings](#local-settings)) |
| In code | `Membase()` | `Membase(local=True)` |
| Command line | `membase …` | `membase --local …`, `membase --local serve`, `membase --local mcp` |
| Install size, Python | small (httpx), 3.10+ | the engine (torch, faiss), Python 3.12 or 3.13 |

The methods and response shapes are the same either way; code moves between hosted and local
memory by changing the constructor. TypeScript: `npm install membase-ai`
([typescript/](https://github.com/unibaseio/membase-ai/tree/main/typescript)). Install `membase-ai`, not `membase`: that is an unrelated package
with the same import name.

```python
from membase import Membase

m = Membase()                    # hosted: MEMBASE_API_KEY (Connect › Developer keys)
# m = Membase(local=True)        # or local: ~/.membase

m.memories.add("We picked Postgres for the ledger service.", container="Engineering")
m.search("what database is the ledger on?")
m.add("Design notes …", container="Engineering", custom_id="design-1")   # a document
m.profile()
m.ask("Which database did we choose for the ledger?")   # hosted, this needs an agent-endpoint key
```

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/operations.svg" width="840" alt="Agent protocol operations and client methods">
</p>

Every method is one operation of the Membase agent protocol. Hosted, the service enforces each
key's reach and access level. Local, the same operations run on the
[membase-core](https://pypi.org/project/membase-core/) engine, and search is its multi-round
retrieval. Removing a document or forgetting a memory needs `confirm=True` in both.

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/memory-types.svg" width="840" alt="Conversations, documents and agent traces">
</p>


## Command line

```bash
membase --local add "We picked Postgres for the ledger" --container Engineering
membase --local search "what did we pick for the ledger?"
membase --local ask "Which database is the ledger on?"
membase --local import ~/Downloads/claude-export.json     # Claude / ChatGPT / markdown / JSON chats
membase --local import ~/chats/ --dry-run                 # a directory, scanned; --dry-run only reports
membase --local documents add notes.md --container Engineering
membase --local profile
membase --local agent ingest trace.json --agent coder     # agent memory: traces -> cases and skills
membase --local agent search "fix flaky deploy" --agent coder
```

`--local` and `--store DIR` go before the command. Without them the commands use the hosted API
(`MEMBASE_API_KEY`), except `agent` and `serve`, which are local only; `import` needs
`membase-ai[local]` either way to read the exports, and hosted it stores each chat as a document.
`MEMBASE_LOCAL=1` (or a directory) makes local the default when `MEMBASE_API_KEY` is not set.

## MCP

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/mcp.svg" width="840" alt="MCP clients, hosted or local server, same tools">
</p>

```bash
claude mcp add membase -- membase --local mcp       # local memory
claude mcp add --transport http membase https://api.app.membase.io/mcp-http \
  --header "Authorization: Bearer $MEMBASE_API_KEY"  # hosted, at the key's access level
```

Hosted without the header, the client signs in and the connection is read-only. The local server
offers the hosted endpoint's agent-protocol tools: `list_containers`, `search_memories`,
`get_profile`, `list_documents`, `memory_rules`, `add_memory`, `add_document`,
`delete_document`, `forget_memory`, `ask_agent`.

## Local memory over HTTP

```bash
membase --local serve            # http://127.0.0.1:8787/v1
```

`membase serve` answers the agent-protocol routes of the hosted API (containers, search, profile,
rules, documents, memories, ask) from the local engine, so the TypeScript client, or anything else
that speaks the API, can use local memory by pointing its base URL at it. With
`MEMBASE_LOCAL_TOKEN` set, every request must carry that token as its bearer.

## Local settings

Local stores: the `default` container is `~/.membase/memory.db`, others are
`~/.membase/containers/<id>/`, and standing (`static`) profile facts are in
`~/.membase/profile/`. The engine reads its settings from the environment, and from a `.env` file
in the current directory or a parent without overriding what is already set:

| Setting | Default | |
|---|---|---|
| `OPENAI_API_KEY` | | chat (the default provider) and embeddings |
| `MEMBASE_LLM_PROVIDER` | `openai` when `OPENAI_API_KEY` is set | `anthropic` (with `ANTHROPIC_API_KEY`), `ollama` or `openai-compat` (with `MEMBASE_LLM_ENDPOINT`) for chat; then set the model names below to that provider's models |
| `MEMBASE_EMBED_PROVIDER` | `openai` | `openai-compat` sends embeddings to `MEMBASE_LLM_ENDPOINT` instead |
| `MEMBASE_EMBED_MODEL` | `text-embedding-3-small` | embeddings |
| `MEMBASE_EPISODE_MODEL` | `gpt-4.1-mini` | turns conversations into episodes |
| `MEMBASE_DECIDER_MODEL` | `gpt-4o-mini` | picks the episodes a search returns |
| `MEMBASE_READER_MODEL` | `gpt-4o` | writes `ask` answers |
| `MEMBASE_KNOWLEDGE_MODEL` | `gpt-4o-mini` | reads documents into topic trees |
| `MEMBASE_AGENT_MODEL` | `gpt-4o-mini` | `membase agent ingest` |
| `MEMBASE_LANG` | `en` | `zh` for Chinese extraction prompts |

## Where things live

| | |
|---|---|
| `membase/client.py` | the client (hosted, or local through `membase/local`) |
| `membase/local/` | the agent protocol over membase-core: backend, routes, `membase serve` |
| `membase/mcp/` | `membase mcp` |
| `membase/cli.py` | `membase` |
| `typescript/` | the npm package |

`membase-sdk` (PyPI and npm) is the earlier name of this package and is kept as an alias.

## License

MIT, for this repository: the client, command line, MCP server and TypeScript package.
`membase-ai[local]` also installs the compiled membase-core engine, which is under Unibase's
proprietary license.
