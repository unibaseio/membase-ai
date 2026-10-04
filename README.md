# membase-ai

Membase — long-term memory for AI. One API for the hosted Membase service and for memory that
runs on your own machine, with a command line and an MCP server.

```bash
pip install membase-ai                 # hosted (just httpx)
pip install 'membase-ai[local]'        # + the local engine, membase-core (Python 3.12+; OpenAI,
                                       #   Anthropic or Ollama models; images, PDFs, web pages)
pip install 'membase-ai[local,mcp]'    # + the MCP server
npm install membase-ai                 # TypeScript client (see typescript/)
```

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
membase --local documents add notes.md --container Engineering
membase --local profile
```

Without `--local` the same commands use the hosted API (`MEMBASE_API_KEY`). `MEMBASE_LOCAL=1`
(or a directory) makes local the default.

## MCP

```bash
claude mcp add membase -- membase --local mcp           # local memory
claude mcp add membase -e MEMBASE_API_KEY=mbk_… -- membase mcp   # hosted memory
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
