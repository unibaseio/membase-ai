"""The server over real MCP stdio: the tool surface, and the tools that need no LLM or key."""

from __future__ import annotations

import asyncio
import os
import sys


EXPECTED = {
    "memory_status", "memory_search", "memory_answer", "memory_ingest",
    "automem_save", "automem_list", "automem_fetch", "automem_delete",
    "knowledge_ingest", "knowledge_search", "agent_ingest", "agent_search", "agent_skills",
}


async def _drive(db_path, env):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable, args=["-m", "membase_mcp", "--db", str(db_path)], env=env,
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = {t.name for t in (await session.list_tools()).tools}
        status = await session.call_tool("memory_status", {})
        automem = await session.call_tool("automem_list", {})
        return tools, status, automem


def test_stdio_server(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "MEMBASE_PRIVATE_KEY"}
    tools, status, automem = asyncio.run(_drive(tmp_path / "m.db", env))
    assert tools == EXPECTED
    assert not status.isError and "membase" in status.content[0].text.lower()
    # Without a wallet key the automem tools answer with an error instead of writing anywhere.
    assert automem.isError and "MEMBASE_PRIVATE_KEY" in automem.content[0].text

