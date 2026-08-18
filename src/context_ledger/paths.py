from __future__ import annotations

import subprocess
from pathlib import Path


def project_path(project: Path | None = None) -> Path:
    """Return the explicit project path, or the harness working directory."""
    path = (project or Path.cwd()).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"Project path is not a directory: {path}")
    return path


def database_path(project: Path | None = None) -> Path:
    """Store memory in project Git metadata, falling back to .memory."""
    root = project_path(project)
    if not (root / ".git").exists():
        return root / ".memory" / "memory.sqlite"

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise RuntimeError(f"Unable to run Git in {root}: {error}") from error
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Unable to locate Git metadata in {root}")
    return Path(result.stdout.strip()).resolve() / "llm-memory" / "memory.sqlite"
