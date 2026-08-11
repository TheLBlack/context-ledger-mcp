from __future__ import annotations

import subprocess
from pathlib import Path


def find_repository_root(start: Path | None = None) -> Path:
    """Return the enclosing Git worktree root, failing outside a repository."""
    cwd = (start or Path.cwd()).resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise RuntimeError(f"Unable to run Git in {cwd}: {error}") from error
    if result.returncode != 0:
        raise RuntimeError(f"ContextLedger must run inside a Git repository: {cwd}")
    return Path(result.stdout.strip()).resolve()


def database_path(start: Path | None = None) -> Path:
    """Locate storage in Git-private metadata, shared by linked worktrees."""
    root = find_repository_root(start)
    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unable to locate Git metadata")
    return Path(result.stdout.strip()).resolve() / "llm-memory" / "memory.sqlite"


def resolve_database_path(repository: Path | None = None, database: Path | None = None) -> Path:
    """Use an explicit database path, or derive one from Git-private metadata."""
    if repository is not None and database is not None:
        raise ValueError("repository and database are mutually exclusive")
    if database is not None:
        return database.expanduser().resolve()
    return database_path(repository)
