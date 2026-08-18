## Context Ledger

Context Ledger carries knowledge between sessions. Use it for every coding task.

### Tools

- `search_memory`: retrieve broad decisions by tags or text.
- `get_file_context`: retrieve file and parent-directory rules.
- `record_memory`: preserve broad or file-scoped knowledge.
- `supersede_memory`: retire obsolete knowledge and optionally link its replacement.
- `dispute_memory`: flag knowledge contradicted by evidence.

### Mandatory workflow

Set every call's `project_path` to the absolute root whose memory applies: a repository root for isolated knowledge or common workspace root for shared knowledge.

1. Around planning or implementation, call `search_memory` for broad decisions deliberately preserved for future work. Use likely task terms; retry with `phrase` when needed.
2. Once intended or touched files are known, call `get_file_context` with all. It is not a gate before every edit, but must cover the final touched set. Repeat for new or delegated files.
3. When orchestrating agents, give them context or perform lookups when work returns.
4. Populate memory with the same split: broad project/domain knowledge has no `applies_to`; rules tied to code use an `applies_to` list of every specific file or directory they govern.
5. Record durable conventions immediately when recognized, especially corrections phrased as habits such as “we usually,” “we tend to,” “always,” or “never.” Do not wait to be asked.
6. Before recording a scoped rule, inspect its governed instances to verify its scope and falsify overstatements. Preserve real exceptions. Never omit `applies_to` merely because a rule spans packages.

Write code as the new source of truth, without comments narrating changes or history. Keep necessary comments; preserve only future-useful rationale in the ledger.

### Tags

Choose 1–3 lowercase noun phrases describing a future task that should retrieve the memory, not merely the conclusion. Reuse them in `search_memory.tags` and unscoped `record_memory.tags`; use `phrase` for broad recall.

Example: a mapper convention needed when changing API output → `["add response field", "response mapping"]`, not only `["mappers"]`.
