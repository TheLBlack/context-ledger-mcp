from context_ledger.server import load_harness_snippet, load_instructions


def test_shared_prompt_is_loaded_from_packaged_file():
    instructions = load_instructions()
    assert "Search broad decisions by task terms" in instructions
    assert "including delegated work" in instructions
    assert len(instructions.split()) < 40


def test_harness_snippet_enforces_retrieval_and_careful_capture():
    snippet = load_harness_snippet()
    assert "broad decisions deliberately preserved" in snippet
    assert "get_file_context" in snippet
    assert "absolute root whose memory applies" in snippet
    assert "common workspace root" in snippet
    assert "When orchestrating agents" in snippet
    assert "not a gate before every edit" in snippet
    assert "final touched set" in snippet
    assert "same split" in snippet
    assert "list of every specific file or directory" in snippet
    assert "Do not wait to be asked" in snippet
    assert "falsify overstatements" in snippet
    assert "spans packages" in snippet
    assert "optionally link its replacement" in snippet
    assert "contradicted by evidence" in snippet
    assert "new source of truth" in snippet
    assert "without comments narrating changes or history" in snippet
    assert "future-useful rationale in the ledger" in snippet
    assert '["add response field", "response mapping"]' in snippet
    assert 'not only `["mappers"]`' in snippet
    assert "record_memory.tags" in snippet
    assert len(snippet.split()) < 320
