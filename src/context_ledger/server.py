from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .ledger import Authority, Ledger, RecordKind
from .paths import database_path


def load_instructions() -> str:
    return files("context_ledger.prompts").joinpath("server_instructions.md").read_text(encoding="utf-8")


def load_harness_snippet() -> str:
    return files("context_ledger.prompts").joinpath("harness_snippet.md").read_text(encoding="utf-8")


def create_server() -> FastMCP:
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
    def get_file_context(project_path: str, paths: list[str], limit: int = 20) -> list[dict[str, Any]]:
        """Get active rules for files, including rules attached to their parent directories."""
        with Ledger(database_path(Path(project_path))) as ledger:
            return [item.to_dict() for item in ledger.file_context(paths, limit=limit)]

    @server.tool()
    def search_memory(
        project_path: str,
        tags: list[str] | None = None,
        phrase: str | None = None,
        include_inactive: bool = False,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search by 1–3 exact tags, a broad free-text phrase, or both."""
        with Ledger(database_path(Path(project_path))) as ledger:
            return [
                item.to_dict()
                for item in ledger.search(tags, phrase, include_inactive=include_inactive, limit=limit)
            ]

    @server.tool()
    def record_memory(
        project_path: str,
        kind: RecordKind,
        title: str,
        content: str,
        authority: Authority,
        source: str | None = None,
        applies_to: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Record durable knowledge, optionally scoped to a project-relative path and tagged for search."""
        with Ledger(database_path(Path(project_path))) as ledger:
            return ledger.record(kind, title, content, authority, source, applies_to, tags).to_dict()

    @server.tool()
    def supersede_memory(
        project_path: str, record_id: int, replacement_id: int | None = None
    ) -> dict[str, Any]:
        """Mark obsolete memory superseded, optionally linking its active replacement."""
        with Ledger(database_path(Path(project_path))) as ledger:
            return ledger.supersede(record_id, replacement_id).to_dict()

    @server.tool()
    def dispute_memory(project_path: str, record_id: int) -> dict[str, Any]:
        """Mark a record disputed when evidence conflicts but no replacement is established."""
        with Ledger(database_path(Path(project_path))) as ledger:
            return ledger.dispute(record_id).to_dict()

    return server
