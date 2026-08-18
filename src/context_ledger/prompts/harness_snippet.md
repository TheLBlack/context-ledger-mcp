## Context Ledger

Context Ledger carries knowledge between sessions. Use it on every coding task.

### Tools

- `get_file_context`: retrieve file and parent-directory knowledge for a project.
- `search_memory`: find preserved project knowledge by tags, free text, or both.
- `record_memory`: preserve a conclusion, optionally scoped with `applies_to` and tags.
- `supersede_memory`: retire obsolete knowledge and optionally link its replacement.
- `dispute_memory`: flag knowledge contradicted by evidence when no replacement is established.

### Mandatory workflow

On every call, set `project_path` to the absolute root whose memory applies. Use a repository root for isolated knowledge or a common workspace root for shared knowledge.

1. Around planning or implementation, call `search_memory` for past decisions deliberately preserved for future work. Retry with better tags or `phrase` when needed.
2. Call `get_file_context` once touched or intended files are known. It is not a gate before every edit: lookup may happen before or after changes, but must cover the final touched set. Repeat for new files.
3. When orchestrating agents, pass them context or perform these lookups when their work returns.
4. Proactively populate the ledger: record decisions, constraints, conventions, failed approaches, and non-obvious reasons worth preserving. Set `applies_to` for knowledge tied to a file or directory; otherwise omit it. Skip routine progress and obvious facts.

Write code as the new source of truth, without comments narrating changes or history. Keep necessary comments; preserve future-useful rationale in the ledger.

Example: search with `project_path="/work/app"` → file lookup for `src/auth/tokens.py` → work → record a lasting rule with the same project path and `applies_to="src/auth"`.

### Tags

Turn the task into 1–3 lowercase noun phrases for `search_memory.tags` and unscoped `record_memory.tags`. Prefer prompt or code names; omit verbs, filler, and synonyms. Use `search_memory.phrase` for broad recall.

Example: “Fix refresh-token expiry in auth middleware” → `["refresh token", "token expiry", "auth middleware"]`; search with that list and save the same list on lasting domain memory.
