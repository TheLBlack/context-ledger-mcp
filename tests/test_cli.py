import json
import subprocess
from pathlib import Path

from context_ledger.cli import run


def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def test_cli_init_record_search_and_status(tmp_path: Path, capsys):
    repo = git_repo(tmp_path)
    common = ["--repository", str(repo)]

    assert run(["init", *common]) == 0
    capsys.readouterr()
    assert run(["record", *common, "decision", "Database", "Use SQLite", "--authority", "user_confirmed"]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["title"] == "Database"

    assert run(["search", *common, "SQLite"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output[0]["kind"] == "decision"

    assert run(["status", *common]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["active_records"]["decision"] == 1
    assert status["database"].endswith(".git/llm-memory/memory.sqlite")


def test_cli_prompt_matches_runtime_instructions(capsys):
    from context_ledger.server import load_instructions

    assert run(["prompt"]) == 0
    assert capsys.readouterr().out == load_instructions()


def test_cli_snippet_matches_packaged_harness_snippet(capsys):
    from context_ledger.server import load_harness_snippet

    assert run(["snippet"]) == 0
    assert capsys.readouterr().out == load_harness_snippet()


def test_cli_serve_reports_invalid_repository_without_traceback(tmp_path: Path, capsys):
    missing = tmp_path / "missing"

    assert run(["serve", "--repository", str(missing)]) == 2
    error = capsys.readouterr().err
    assert "Unable to run Git" in error
    assert "Traceback" not in error


def test_cli_explicit_database_works_outside_git(tmp_path: Path, capsys):
    database = tmp_path / "shared" / "memory.sqlite"
    common = ["--database", str(database)]

    assert run(["record", *common, "decision", "Scope", "Share this ledger", "--authority", "user_confirmed"]) == 0
    capsys.readouterr()
    assert run(["status", *common]) == 0
    status = json.loads(capsys.readouterr().out)

    assert status["database"] == str(database)
    assert status["active_records"]["decision"] == 1
    assert "repository" not in status


def test_cli_rejects_repository_and_database_together(tmp_path: Path, capsys):
    repo = git_repo(tmp_path / "repo")

    try:
        run(["status", "--repository", str(repo), "--database", str(tmp_path / "memory.sqlite")])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("argparse should reject conflicting storage options")

    assert "not allowed with argument" in capsys.readouterr().err
