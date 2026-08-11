# ContextLedger — mandatory startup workflow

ContextLedger is the current scope's durable architectural memory. A scope may be one repository or a group sharing the same ledger. When this server is available, call `get_project_context` with a concise task description before planning or changing code. Do not wait for the user to request it. These server-wide instructions arrive during MCP initialization and apply even when tools are deferred. ContextLedger primarily exposes tools; an empty MCP resource listing does not mean the server is unavailable. Use `search_memory` when you need broader or historical detail.

Record only conclusions likely to matter in a later session, never transcripts or routine progress. Classify every entry accurately:

- `decision`: an intentional choice; use `user_confirmed` unless the user explicitly delegates the choice.
- `observation`: a durable fact found in code or behavior; normally use `code_observed`.
- `documentation`: stable explanatory project knowledge.
- `failed_attempt`: an approach that failed and why, when repeating it would waste time.

Authority is evidence, not confidence: `user_confirmed`, `code_observed`, or `agent_inferred`. Never turn an observation or inference into a user decision. Supersede obsolete records instead of deleting them; dispute records when evidence conflicts and no replacement is established. Keep titles specific and content compact, including file or command provenance in `source` when useful.
