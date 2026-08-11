import subprocess
from pathlib import Path

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

from context_ledger.server import create_server, load_instructions


@pytest.mark.anyio
async def test_initialize_response_contains_canonical_instructions(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    server = create_server(tmp_path)

    async with create_client_server_memory_streams() as (client_streams, server_streams):
        client_read, client_write = client_streams
        server_read, server_write = server_streams
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(
                server._mcp_server.run,
                server_read,
                server_write,
                server._mcp_server.create_initialization_options(),
            )
            try:
                async with ClientSession(client_read, client_write) as session:
                    result = await session.initialize()
                    assert result.instructions == load_instructions()
            finally:
                task_group.cancel_scope.cancel()


@pytest.mark.anyio
async def test_mcp_tools_are_registered_and_callable(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    server = create_server(tmp_path)

    tools = {tool.name: tool for tool in await server.list_tools()}
    assert set(tools) == {
        "get_project_context",
        "search_memory",
        "record_memory",
        "supersede_memory",
        "dispute_memory",
    }
    assert tools["record_memory"].inputSchema["properties"]["kind"]["enum"] == [
        "decision",
        "observation",
        "documentation",
        "failed_attempt",
    ]

    resources = {str(resource.uri): resource for resource in await server.list_resources()}
    assert resources["ledger://instructions"].mimeType == "text/markdown"
    contents = list(await server.read_resource("ledger://instructions"))
    assert contents[0].content == load_instructions()

    _, recorded = await server.call_tool(
        "record_memory",
        {
            "kind": "decision",
            "title": "Database",
            "content": "Use SQLite",
            "authority": "user_confirmed",
        },
    )
    _, context = await server.call_tool("get_project_context", {"task": "SQLite"})

    assert recorded["title"] == "Database"
    assert context["result"][0]["id"] == recorded["id"]
    assert server.instructions == load_instructions()
