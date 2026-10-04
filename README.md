# membase-ai

Long-term memory for AI agents and apps — hosted, or on your machine.

| | `pip install membase-ai` | `pip install 'membase-ai[local]'` |
|---|---|---|
| Memory lives | in your Membase account (hosted) | on this machine, under `~/.membase` |
| You need | an API key (`MEMBASE_API_KEY`) | a model key of your own (OpenAI, Anthropic or Ollama) |
| In code | `Membase()` | `Membase(local=True)` |
| Command line | `membase …` | `membase --local …`, `membase --local serve`, `membase --local mcp` |
| Install size, Python | small (httpx), 3.10+ | the engine (torch, faiss), 3.12+ |

The API is the same either way; code moves between hosted and local memory by changing the
constructor. TypeScript: `npm install membase-ai` (see `typescript/`).

```python
from membase import Membase

m = Membase()                    # hosted: MEMBASE_API_KEY (Connect › Developer keys)
m = Membase(local=True)          # local: ~/.membase, same methods, same answers

m.memories.add("We picked Postgres for the ledger service.", container="Engineering")
m.search("what database is the ledger on?")
m.ask("Which database did we choose for the ledger?")
m.add("Design notes …", container="Engineering", custom_id="design-1")   # a document
m.profile()
```

Every method is one operation of the Membase agent protocol (`list_containers`,
`search_memories`, `get_profile`, `list_documents`, `memory_rules`, `add_memory`,
`add_document`, `delete_document`, `forget_memory`, `ask_agent`). Hosted, the service enforces
each key's reach and access level. Local, the same routes are answered by the
[membase-core](https://github.com/unibaseio/membase-core) engine: a memory becomes dated
episodes, a document becomes a topic tree, and search is the engine's multi-round retrieval.
Removing a document or forgetting a memory needs `confirm=True` in both.

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

Without `--local` the same commands use the hosted API (`MEMBASE_API_KEY`). `MEMBASE_LOCAL=1`
(or a directory) makes local the default.

## MCP

```bash
claude mcp add membase -- membase --local mcp           # local memory
claude mcp add --transport http membase https://api.app.membase.io/mcp-http   # hosted memory, nothing to install
```

The server offers the same tools as the hosted endpoint (`https://api.app.membase.io/mcp-http`),
so a client sees one tool set either way. With membase-protocol installed and `MEMBASE_PRIVATE_KEY`
it also offers `automem_save` / `automem_list` / `automem_fetch` / `automem_delete`: a client's
auto-memory notes, signed and encrypted by the wallet and kept on the Membase Hub, restorable on
any device with the same key.

## Local memory over HTTP

```bash
membase --local serve            # http://127.0.0.1:8787/v1
```

`membase serve` answers the `/v1` routes of the hosted API from the local engine, so the
TypeScript client — or anything else that speaks the API — can use local memory by pointing its
base URL at it. Set `MEMBASE_LOCAL_TOKEN` to require a bearer token.

## Where things live

| | |
|---|---|
| `membase/client.py` | the client (hosted, or local through `membase/local`) |
| `membase/local/` | the agent protocol over membase-core: backend, routes, `membase serve` |
| `membase/mcp/` | `membase mcp`, and the automem tools |
| `membase/cli.py` | `membase` |
| `typescript/` | the npm package |

Local stores: the `default` container is `~/.membase/memory.db`; others are
`~/.membase/containers/<id>/`. Settings for the engine (models, providers) are the `MEMBASE_*`
variables documented in membase-core.

`membase-sdk` (PyPI and npm) is the earlier name of this package and is kept as an alias.

## License

MIT.
