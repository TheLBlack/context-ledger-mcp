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
    server = create_server()

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
    server = create_server()

    tools = {tool.name: tool for tool in await server.list_tools()}
    assert set(tools) == {
        "get_file_context",
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
    for tool in tools.values():
        assert "project_path" in tool.inputSchema["required"]
    assert "kind" not in tools["search_memory"].inputSchema["properties"]
    assert "tags" in tools["search_memory"].inputSchema["properties"]
    assert "phrase" in tools["search_memory"].inputSchema["properties"]
    assert "query" not in tools["search_memory"].inputSchema["properties"]
    search_tags_schema = tools["search_memory"].inputSchema["properties"]["tags"]["anyOf"][0]
    assert search_tags_schema["items"]["type"] == "string"
    assert tools["record_memory"].inputSchema["properties"]["tags"]["anyOf"][0]["type"] == "array"

    resources = {str(resource.uri): resource for resource in await server.list_resources()}
    assert resources["ledger://instructions"].mimeType == "text/markdown"
    contents = list(await server.read_resource("ledger://instructions"))
    assert contents[0].content == load_instructions()

    _, recorded = await server.call_tool(
        "record_memory",
        {
            "project_path": str(tmp_path),
            "kind": "decision",
            "title": "Database",
            "content": "Use SQLite",
            "authority": "user_confirmed",
        },
    )
    _, context = await server.call_tool(
        "search_memory", {"project_path": str(tmp_path), "tags": ["SQLite"]}
    )

    assert recorded["title"] == "Database"
    assert context["result"][0]["id"] == recorded["id"]
    assert server.instructions == load_instructions()

    _, scoped = await server.call_tool(
        "record_memory",
        {
            "project_path": str(tmp_path),
            "kind": "observation",
            "title": "Server rule",
            "content": "Keep MCP handlers small",
            "authority": "code_observed",
            "applies_to": "src/context_ledger",
        },
    )
    _, file_context = await server.call_tool(
        "get_file_context",
        {"project_path": str(tmp_path), "paths": ["src/context_ledger/server.py"]},
    )
    assert file_context["result"][0]["id"] == scoped["id"]


@pytest.mark.anyio
async def test_mcp_routes_each_call_by_project_path(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    server = create_server()

    _, recorded = await server.call_tool(
        "record_memory",
        {
            "project_path": str(first),
            "kind": "decision",
            "title": "First project only",
            "content": "Keep this isolated",
            "authority": "user_confirmed",
        },
    )
    _, first_results = await server.call_tool(
        "search_memory", {"project_path": str(first), "tags": ["isolated"]}
    )
    _, second_results = await server.call_tool(
        "search_memory", {"project_path": str(second), "tags": ["isolated"]}
    )

    assert first_results["result"][0]["id"] == recorded["id"]
    assert second_results["result"] == []
