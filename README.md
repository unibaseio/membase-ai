# membase-mcp

MCP server for the Membase memory engine ([membase-algo](https://github.com/unibaseio/unibase-supermem)).
It gives Claude Code, Claude Desktop, Cursor or any MCP client long-term memory on your own
machine, and optionally backs up auto-memory to the Membase Protocol hub.

> The previous version of this repository (a conversation log on the legacy hub SDK) is kept
> at tag [`v0`](../../tree/v0).

## Install

```bash
pip install 'membase-mcp @ git+https://github.com/unibaseio/membase-mcp.git'
# with automem backup on the Membase Protocol hub:
pip install 'membase-mcp[protocol] @ git+https://github.com/unibaseio/membase-mcp.git'
```

Python 3.12+. The engine needs an LLM and embedding provider (`OPENAI_API_KEY`, or see the
engine's README); `--no-llm` keeps retrieval verbatim.

## Connect

```bash
claude mcp add membase -- membase-mcp
```

or in an MCP client config:

```json
{ "mcpServers": { "membase": { "command": "membase-mcp", "args": [] } } }
```

Options: `--db PATH` (default `SUPERMEM_DB` or `~/.supermem/memory.db`, the engine's store),
`--no-llm`, `--transport stdio|sse|streamable-http`, `--host`, `--port`.

## Tools

| Tool | What |
|---|---|
| `memory_status` | Returns the Memory Protocol behaviour guide. Call once per session. |
| `memory_search` | Semantic search; verbatim ranked hits. |
| `memory_answer` | Retrieval + reader: a synthesized answer over several memories. |
| `memory_ingest` | File a session into memory. |
| `knowledge_ingest` / `knowledge_search` | Documents to a topic tree; category-boosted search. |
| `agent_ingest` / `agent_search` / `agent_skills` | Agent traces to cases and skills. |
| `automem_save` / `automem_list` / `automem_fetch` / `automem_delete` | Auto-memory backup on the hub (below). |

## Auto-memory backup

The `automem_*` tools keep a durable copy of a client's auto-memory (for Claude Code,
`~/.claude/projects/<repo>/memory/*.md`) on the Membase Protocol hub. Install the `[protocol]`
extra and set a wallet key:

```bash
export MEMBASE_PRIVATE_KEY=0x...   # environment only; never passed on the command line
export MEMBASE_HUB=https://testnet.hub.membase.io   # optional; default is the SDK's hub
```

Entries are signed by the wallet and encrypted with a key derived from it, so the same key
restores the backup on another device. The hub keeps each object write-once, so the backup is
an append-only log in the wallet's `automem` domain: each save and delete is one entry, and the
current state is the log replayed in order. Two devices writing at once cannot lose each
other's entries.

Same `(scope, name)` gives the same id, so re-saving updates the record in place. A delete
hides the record; its earlier entries stay on the hub, encrypted.

## Development

```bash
uv venv --python 3.12 && uv pip install --torch-backend cpu -e '.[protocol,dev]'
pytest                      # offline
MEMBASE_MCP_TEST_HUB=1 pytest tests/test_automem.py   # also against the real hub
```

## License

MIT, see [LICENSE](LICENSE).
