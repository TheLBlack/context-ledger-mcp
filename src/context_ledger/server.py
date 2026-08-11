from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .ledger import Authority, Ledger, RecordKind
from .paths import resolve_database_path


def load_instructions() -> str:
    return files("context_ledger.prompts").joinpath("server_instructions.md").read_text(encoding="utf-8")


def load_harness_snippet() -> str:
    return files("context_ledger.prompts").joinpath("harness_snippet.md").read_text(encoding="utf-8")


def create_server(repository: Path | None = None, database: Path | None = None) -> FastMCP:
    ledger = Ledger(resolve_database_path(repository, database))
    server = FastMCP("ContextLedger", instructions=load_instructions())

    @server.resource(
        "ledger://instructions",
        name="context_ledger_instructions",
        title="ContextLedger server instructions",
        description="Diagnostic copy of the server-wide instructions sent during MCP initialization.",
        mime_type="text/markdown",
    )
    def instructions_resource() -> str:
        """Return the canonical server instructions for inspection and debugging."""
        return load_instructions()

    @server.tool()
    def get_project_context(task: str, limit: int = 12) -> list[dict[str, Any]]:
        """Get active, durable project knowledge relevant to the task before planning or editing."""
        return [item.to_dict() for item in ledger.context(task, limit=limit)]

    @server.tool()
    def search_memory(
        query: str, kind: RecordKind | None = None, include_inactive: bool = False, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search durable project memory. Set include_inactive to inspect superseded history."""
        return [item.to_dict() for item in ledger.search(query, kind=kind, include_inactive=include_inactive, limit=limit)]

    @server.tool()
    def record_memory(
        kind: RecordKind, title: str, content: str, authority: Authority, source: str | None = None
    ) -> dict[str, Any]:
        """Record a durable conclusion, classified as decision, observation, documentation, or failed_attempt."""
        return ledger.record(kind, title, content, authority, source).to_dict()

    @server.tool()
    def supersede_memory(record_id: int, replacement_id: int | None = None) -> dict[str, Any]:
        """Mark obsolete memory superseded, optionally linking its active replacement."""
        return ledger.supersede(record_id, replacement_id).to_dict()

    @server.tool()
    def dispute_memory(record_id: int) -> dict[str, Any]:
        """Mark a record disputed when evidence conflicts but no replacement is established."""
        return ledger.dispute(record_id).to_dict()

    return server
