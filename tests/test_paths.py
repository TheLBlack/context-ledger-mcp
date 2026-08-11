import subprocess
from pathlib import Path

import pytest

from context_ledger.paths import database_path, resolve_database_path


def test_database_lives_in_git_private_metadata(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)

    path = database_path(tmp_path)

    assert path == tmp_path / ".git" / "llm-memory" / "memory.sqlite"


def test_explicit_database_does_not_require_git(tmp_path: Path):
    path = resolve_database_path(database=tmp_path / "shared" / "memory.sqlite")

    assert path == tmp_path / "shared" / "memory.sqlite"


def test_repository_and_database_are_mutually_exclusive(tmp_path: Path):
    with pytest.raises(ValueError, match="mutually exclusive"):
        resolve_database_path(tmp_path, tmp_path / "memory.sqlite")
