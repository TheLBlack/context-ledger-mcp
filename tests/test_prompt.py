from context_ledger.server import load_harness_snippet, load_instructions


def test_shared_prompt_is_loaded_from_packaged_file():
    instructions = load_instructions()
    assert "get_project_context" in instructions
    assert "Do not wait for the user" in instructions[:512]
    assert "tools are deferred" in instructions[:512]
    assert "Never turn an observation" in instructions


def test_harness_snippet_enforces_retrieval_and_careful_capture():
    snippet = load_harness_snippet()
    assert "Before planning or changing code" in snippet
    assert "get_project_context" in snippet
    assert "never store transcripts" in snippet
    assert "do not turn an observation or inference into a user decision" in snippet
