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

The Membase SDK: a Python client, the `membase` command line, an MCP server and a TypeScript
client. The memory lives in your Membase account or on your machine, behind the same API.

## How it works

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/hero.svg" width="840" alt="Sources go into one memory that every AI and app reads">
</p>

## See it in action

<table>
  <tr>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/sdk-card.svg" alt="Python SDK: add a memory, search it"><br>
      <b>From your code</b> · <a href="https://github.com/unibaseio/membase-ai/blob/main/assets/videos/sdk.mp4">recording, 57 s</a>
    </td>
    <td width="50%" valign="top">
      <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/mcp-card.svg" alt="Claude Code reads the memory over MCP"><br>
      <b>From Claude Code</b> · <a href="https://github.com/unibaseio/membase-ai/blob/main/assets/videos/switch-ai.mp4">recording, 1 min 33 s</a>
    </td>
  </tr>
</table>

Outputs in the cards are illustrative.

## Benchmarks

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/results.svg" width="840" alt="LoCoMo 93.1%, LongMemEval_S 92.6%, DMR 92.2%">
</p>

## Install

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/architecture.svg" width="840" alt="Hosted, local in process, or local over HTTP">
</p>

```bash
pip install membase-ai              # hosted · Python 3.10+ · needs MEMBASE_API_KEY
pip install 'membase-ai[local]'     # local  · Python 3.12 or 3.13 · needs OPENAI_API_KEY
npm install membase-ai              # TypeScript · Node 18+
```

The package is `membase-ai`; `membase` on PyPI is unrelated.

```python
from membase import Membase

m = Membase()                    # hosted
# m = Membase(local=True)        # local, in ~/.membase

m.memories.add("We picked Postgres for the ledger service.", container="Engineering")
m.search("what database is the ledger on?")
m.add("Design notes …", container="Engineering", custom_id="design-1")   # a document
m.profile()
m.ask("Which database did we choose for the ledger?")
```

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/operations.svg" width="840" alt="Client methods: read, write, remove, answer">
</p>

- Deleting a document or forgetting a memory needs `confirm=True`; without it you get what would be removed.
- Hosted, `ask` needs an agent-endpoint key, and each key is limited to its containers and access level.

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/memory-types.svg" width="840" alt="Conversations, documents and agent traces">
</p>

## Command line

```bash
membase --local add "We picked Postgres for the ledger" --container Engineering
membase --local search "what did we pick for the ledger?"
membase --local ask "Which database is the ledger on?"
membase --local import ~/Downloads/claude-export.json     # Claude, ChatGPT, markdown or JSON chats
membase --local import ~/chats/ --dry-run                 # a directory; --dry-run only reports
membase --local documents add notes.md --container Engineering
membase --local agent ingest trace.json --agent coder
membase --local agent search "fix flaky deploy" --agent coder
```

- `--local` and `--store DIR` go before the command. Without them, commands use the hosted API.
- `agent` and `serve` are local only. `import` needs `membase-ai[local]` to read the exports.
- `MEMBASE_LOCAL=1` makes local the default when `MEMBASE_API_KEY` is not set.

## MCP

<p align="center">
  <img src="https://raw.githubusercontent.com/unibaseio/membase-ai/main/assets/mcp.svg" width="840" alt="MCP clients, hosted or local server, same tools">
</p>

```bash
claude mcp add membase -- membase --local mcp                                   # local
claude mcp add --transport http membase https://api.app.membase.io/mcp-http \
  --header "Authorization: Bearer $MEMBASE_API_KEY"                             # hosted
```

Hosted without the header, the connection signs you in and is read-only.

## Local memory over HTTP

```bash
membase --local serve            # http://127.0.0.1:8787/v1
```

The hosted API's agent-protocol routes, answered by the local engine: point any client's base URL at it. Set
`MEMBASE_LOCAL_TOKEN` to require it as a bearer token.

## Local settings

Stores: `~/.membase/memory.db` (default container), `~/.membase/containers/<id>/` (others),
`~/.membase/profile/` (static facts). Settings come from the environment, or from a `.env` file in
the current directory or a parent.

| Setting | Default | |
|---|---|---|
| `OPENAI_API_KEY` | | chat and embeddings |
| `MEMBASE_LLM_PROVIDER` | from your keys | `openai`, `anthropic`, `ollama` or `openai-compat` for chat; set the models below to match |
| `MEMBASE_LLM_ENDPOINT` | | base URL for `ollama` or `openai-compat` |
| `MEMBASE_EMBED_PROVIDER` | `openai` | `openai-compat` uses `MEMBASE_LLM_ENDPOINT` |
| `MEMBASE_EMBED_MODEL` | `text-embedding-3-small` | embeddings |
| `MEMBASE_EPISODE_MODEL` | `gpt-4.1-mini` | conversations into episodes |
| `MEMBASE_DECIDER_MODEL` | `gpt-4o-mini` | picks the episodes a search returns |
| `MEMBASE_READER_MODEL` | `gpt-4o` | `ask` answers |
| `MEMBASE_KNOWLEDGE_MODEL` | `gpt-4o-mini` | documents into topic trees |
| `MEMBASE_AGENT_MODEL` | `gpt-4o-mini` | agent traces |
| `MEMBASE_LANG` | `en` | `zh` for Chinese extraction prompts |

## Repository

`membase/` is the Python package (`client.py`, `cli.py`, `local/` for local memory and `membase serve`,
`mcp/` for `membase mcp`); `typescript/` is the npm package. `membase-sdk` (PyPI and npm) is the
earlier name, kept as an alias.

## License

MIT. `membase-ai[local]` also installs membase-core, the compiled engine, under Unibase's
proprietary license.
