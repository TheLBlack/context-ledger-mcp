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
    assert {item.kind for item in ledger.search(["SQLite"])} == {"observation", "decision"}
    assert decision.id in [item.id for item in ledger.search(["project memory"])]


def test_search_accepts_literal_tag_phrases(ledger: Ledger):
    record = ledger.record("observation", "Config file", "The config.py module is local", "code_observed")

    assert ledger.search(["config file", "config.py"])[0].id == record.id


def test_search_accepts_free_text_alongside_tags(ledger: Ledger):
    phrase_match = ledger.record(
        "observation", "Authentication middleware", "Refresh tokens expire here", "code_observed"
    )
    tag_match = ledger.record(
        "decision", "Session lifetime", "Keep sessions short", "user_confirmed", tags=["token expiry"]
    )

    found = ledger.search(tags=["token expiry"], phrase="refresh authentication")

    assert {item.id for item in found} == {phrase_match.id, tag_match.id}


def test_superseded_history_is_retained_but_not_default_search(ledger: Ledger):
    old = ledger.record("decision", "Storage", "Store memory in JSON files", "user_confirmed")
    new = ledger.record("decision", "Storage", "Store memory in SQLite", "user_confirmed")
    updated = ledger.supersede(old.id, new.id)

    assert updated.status == "superseded"
    assert updated.superseded_by == new.id
    assert ledger.search(["JSON"]) == []
    assert ledger.search(["JSON"], include_inactive=True)[0].id == old.id


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


def test_file_context_includes_exact_file_and_parent_directories(ledger: Ledger):
    root = ledger.record(
        "documentation", "Repository rule", "Applies everywhere", "code_observed", applies_to="."
    )
    package = ledger.record(
        "observation", "Package rule", "Keep adapters thin", "code_observed", applies_to="src/adapters/"
    )
    exact = ledger.record(
        "decision", "Module rule", "Preserve this wire format", "user_confirmed", applies_to="src/adapters/api.py"
    )
    unrelated = ledger.record(
        "observation", "Other rule", "Only for docs", "code_observed", applies_to="docs"
    )

    found = ledger.file_context(["./src/adapters/api.py", "src/domain.py"])

    assert {item.id for item in found} == {root.id, package.id, exact.id}
    assert unrelated.id not in {item.id for item in found}


def test_tags_are_searchable_without_polluting_file_context(ledger: Ledger):
    record = ledger.record(
        "decision",
        "Persistence boundary",
        "Keep this storage choice",
        "user_confirmed",
        tags=["sqlite", "ledger storage"],
    )

    assert ledger.search(["sqlite"])[0].id == record.id
    assert ledger.file_context(["src/context_ledger/ledger.py"]) == []
