import json
import subprocess
from pathlib import Path

import pytest

from context_ledger.cli import run


def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def test_cli_init_record_search_and_status(tmp_path: Path, capsys):
    repo = git_repo(tmp_path)
    common = ["--project", str(repo)]

    assert run(["init", *common]) == 0
    capsys.readouterr()
    assert run(["record", *common, "decision", "Database", "Use SQLite", "--authority", "user_confirmed"]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["title"] == "Database"

    assert run(["search", *common, "--tags", "SQLite"]) == 0
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


def test_cli_serve_does_not_accept_a_project(capsys):
    with pytest.raises(SystemExit) as error:
        run(["serve", "--project", "/tmp/project"])

    assert error.value.code == 2
    assert "unrecognized arguments: --project" in capsys.readouterr().err


def test_cli_project_works_outside_git(tmp_path: Path, capsys):
    common = ["--project", str(tmp_path)]

    assert run(["record", *common, "decision", "Scope", "Keep this ledger", "--authority", "user_confirmed"]) == 0
    capsys.readouterr()
    assert run(["status", *common]) == 0
    status = json.loads(capsys.readouterr().out)

    assert status["project"] == str(tmp_path)
    assert status["database"] == str(tmp_path / ".memory" / "memory.sqlite")
    assert status["active_records"]["decision"] == 1


def test_cli_does_not_offer_kind_filters(tmp_path: Path, capsys):
    repo = git_repo(tmp_path)

    for command in ("list", "search"):
        arguments = [command, "--project", str(repo), "--kind", "decision"]
        if command == "search":
            arguments.extend(["--tags", "SQLite"])
        with pytest.raises(SystemExit) as error:
            run(arguments)
        assert error.value.code == 2
        assert "unrecognized arguments: --kind" in capsys.readouterr().err
