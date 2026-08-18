import subprocess
from pathlib import Path

from context_ledger.paths import database_path, project_path


def test_database_lives_in_git_private_metadata(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)

    path = database_path(tmp_path)

    assert path == tmp_path / ".git" / "llm-memory" / "memory.sqlite"


def test_database_falls_back_to_project_memory_directory(tmp_path: Path):
    path = database_path(tmp_path)

    assert path == tmp_path / ".memory" / "memory.sqlite"


def test_project_defaults_to_working_directory(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert project_path() == tmp_path
    assert database_path() == tmp_path / ".memory" / "memory.sqlite"
