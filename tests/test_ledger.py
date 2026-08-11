from pathlib import Path

import pytest

from context_ledger.ledger import Ledger


@pytest.fixture
def ledger(tmp_path: Path):
    with Ledger(tmp_path / "memory.sqlite") as instance:
        yield instance


def test_records_separate_kinds_and_searches_active_memory(ledger: Ledger):
    decision = ledger.record("decision", "Use SQLite", "Keep project memory local in SQLite", "user_confirmed")
    ledger.record("observation", "Current database", "SQLite supports FTS5 here", "code_observed", "tests")

    assert decision.kind == "decision"
    assert {item.kind for item in ledger.search("SQLite")} == {"observation", "decision"}
    assert decision.id in [item.id for item in ledger.context("local SQLite")]


def test_plain_language_query_does_not_expose_fts_syntax(ledger: Ledger):
    record = ledger.record("observation", "Config file", "The config.py module is local", "code_observed")

    assert ledger.search("Where is config.py?")[0].id == record.id


def test_superseded_history_is_retained_but_not_default_search(ledger: Ledger):
    old = ledger.record("decision", "Storage", "Store memory in JSON files", "user_confirmed")
    new = ledger.record("decision", "Storage", "Store memory in SQLite", "user_confirmed")
    updated = ledger.supersede(old.id, new.id)

    assert updated.status == "superseded"
    assert updated.superseded_by == new.id
    assert ledger.search("JSON") == []
    assert ledger.search("JSON", include_inactive=True)[0].id == old.id


def test_replacement_must_preserve_record_kind(ledger: Ledger):
    decision = ledger.record("decision", "Choice", "Choose the API", "user_confirmed")
    observation = ledger.record("observation", "API", "The API exists", "code_observed")

    with pytest.raises(ValueError, match="same kind"):
        ledger.supersede(decision.id, observation.id)
    # A rejected transition must roll back its transaction and leave the ledger usable.
    assert ledger.record("decision", "Still usable", "Transactions recover", "agent_inferred").status == "active"


def test_disputed_record_can_later_be_superseded(ledger: Ledger):
    old = ledger.record("decision", "API", "Use the old API", "user_confirmed")
    new = ledger.record("decision", "API", "Use the new API", "user_confirmed")

    assert ledger.dispute(old.id).status == "disputed"
    replaced = ledger.supersede(old.id, new.id)

    assert replaced.status == "superseded"
    assert replaced.superseded_by == new.id


def test_rejects_invalid_classification(ledger: Ledger):
    with pytest.raises(ValueError, match="Invalid authority"):
        ledger.record("decision", "Choice", "Something", "certain")  # type: ignore[arg-type]
