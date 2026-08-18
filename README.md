# ContextLedger

Local, explicitly scoped memory for coding agents.

ContextLedger lets an agent keep useful project knowledge between sessions: architectural decisions, code observations, durable documentation, and failed approaches worth avoiding. It stores conclusions, not chat transcripts.

Many agent-memory products assume organization-wide adoption, cloud infrastructure, or a new company policy. ContextLedger is for the developer who wants durable agent memory today: install it locally, bind it to the projects you choose, and keep the data inside those projects. No cloud deployment, subscription, external account, or company-wide rollout is required.

It is harness- and model-agnostic. ContextLedger exposes standard [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tools over stdio, so any MCP client can use it. Codex and Claude Code are included below as concrete setup examples, not privileged integrations. Give the server a project path and it resolves that project's database automatically. For a Git project, storage lives in private Git metadata:

```text
<project>/.git/llm-memory/memory.sqlite
```

When the project has no `.git`, the database is stored at `<project>/.memory/memory.sqlite`. There is no account, cloud service, telemetry, network server, global index, or required team rollout. Linked Git worktrees share a ledger because they share a Git common directory.

## Quick start

Requirements: Python 3.11 or newer, SQLite with FTS5, and [uv](https://docs.astral.sh/uv/). Normal Python distributions include FTS5. Git is optional.

### 1. Install

From a clone of ContextLedger:

```sh
uv tool install .
command -v context-ledger
context-ledger --help
```

`command -v context-ledger` must print the installed executable file, for example `/Users/alice/.local/bin/context-ledger`. On Windows, use `where context-ledger`. If the command is missing, run `uv tool update-shell`, restart the shell, and repeat the block.

### 2. Add it to an MCP client

ContextLedger uses MCP over standard input/output. Register it once as a global server. Every MCP tool call includes the project path, so the same server works across all projects.

#### Claude Code

Run this complete block once:

```sh
claude mcp add --transport stdio --scope user context-ledger -- \
  "$(command -v context-ledger)" serve
claude mcp get context-ledger

mkdir -p "$HOME/.claude"
if ! grep -Fq "When Context Ledger MCP tools are available" "$HOME/.claude/CLAUDE.md" 2>/dev/null; then
  printf '\n' >> "$HOME/.claude/CLAUDE.md"
  context-ledger snippet >> "$HOME/.claude/CLAUDE.md"
fi
```

The block adds one global server and appends the ContextLedger snippet to Claude Code's personal instructions once. Start a new Claude Code session and run `/mcp` to check the connection. See the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).

#### Codex

Run this complete block once:

```sh
codex mcp add context-ledger -- \
  "$(command -v context-ledger)" serve
codex mcp list

mkdir -p "$HOME/.codex"
if ! grep -Fq "When Context Ledger MCP tools are available" "$HOME/.codex/AGENTS.md" 2>/dev/null; then
  printf '\n' >> "$HOME/.codex/AGENTS.md"
  context-ledger snippet >> "$HOME/.codex/AGENTS.md"
fi
```

The block adds one global server and appends the ContextLedger snippet to Codex's personal instructions once. Start a new Codex session and run `/mcp` to check the connection. See the [Codex MCP documentation](https://developers.openai.com/codex/mcp).

#### Generic MCP client

If the client has no dedicated setup command, add the equivalent stdio server object in its MCP configuration:

```json
{
  "mcpServers": {
    "context-ledger": {
      "command": "/absolute/path/printed/by/command-v/context-ledger",
      "args": ["serve"]
    }
  }
}
```

Use the exact output of `command -v context-ledger` for `command`. The outer property names vary by client; the stdio command and arguments do not.

Append the same harness-neutral snippet to that client's instruction file:

```sh
HARNESS_INSTRUCTIONS="/absolute/path/to/your/harness-instructions.md"
mkdir -p "$(dirname "$HARNESS_INSTRUCTIONS")"
if ! grep -Fq "When Context Ledger MCP tools are available" "$HARNESS_INSTRUCTIONS" 2>/dev/null; then
  echo >> "$HARNESS_INSTRUCTIONS"
  context-ledger snippet >> "$HARNESS_INSTRUCTIONS"
fi
```

If a harness cannot start the server, test the configured executable directly:

```sh
/absolute/path/to/context-ledger --help
/absolute/path/to/context-ledger status --project /absolute/path/to/project
```

Do not test `serve` directly. It waits silently for MCP messages on standard input.

## CLI reference

Direct CLI commands accept `--project PATH` after the command and default to the current working directory. The MCP `serve` command is global and does not take a project; MCP tools provide it per call.

```sh
PROJECT_PATH="$(pwd -P)"

# Create the database and print its path
context-ledger init --project "$PROJECT_PATH"

# Show the project, database path, and active counts
context-ledger status --project "$PROJECT_PATH"

# List records
context-ledger list --project "$PROJECT_PATH"
context-ledger list --project "$PROJECT_PATH" --limit 50
context-ledger list --project "$PROJECT_PATH" --all

# Inspect or search records
context-ledger inspect --project "$PROJECT_PATH" 1
context-ledger search --project "$PROJECT_PATH" --tags sqlite "ledger storage"
context-ledger search --project "$PROJECT_PATH" --phrase "why did the old architecture fail" --all
context-ledger search --project "$PROJECT_PATH" --tags architecture --phrase "old approach"

# Retrieve rules for files and their parent directories
context-ledger file-context --project "$PROJECT_PATH" src/context_ledger/server.py tests/test_server.py

# Record durable knowledge
context-ledger record --project "$PROJECT_PATH" decision \
  "Database choice" \
  "Use SQLite with FTS5; no embeddings initially" \
  --authority user_confirmed \
  --source "architecture discussion" \
  --tags sqlite "ledger storage"

# Record compact knowledge for one file or directory
context-ledger record --project "$PROJECT_PATH" observation \
  "MCP handlers stay thin" \
  "Keep storage and matching logic in ledger.py" \
  --authority code_observed \
  --applies-to src/context_ledger/server.py tests/test_server.py

# Preserve lifecycle history
context-ledger supersede --project "$PROJECT_PATH" 1 --replacement 2
context-ledger dispute --project "$PROJECT_PATH" 3

# Inspect packaged instructions
context-ledger snippet
context-ledger snippet --path
context-ledger prompt
context-ledger prompt --path

# Start the MCP stdio server
context-ledger serve
```

Record kinds are informational metadata: `decision`, `observation`, `documentation`, and `failed_attempt`. Retrieval does not filter by kind. Evidence authorities are `user_confirmed`, `code_observed`, and `agent_inferred`. Authority describes the source of a claim, not confidence in it.

Command results are JSON except for `init`, `prompt`, and `snippet`.

## Project routing

One global MCP server routes each tool call to the supplied `project_path`:

```text
one ContextLedger server
├── project_path=/projects/a → /projects/a/.git/llm-memory/memory.sqlite
└── project_path=/projects/b → /projects/b/.git/llm-memory/memory.sqlite
```

The agent must pass the absolute root whose memory the call concerns. For a workspace containing several repositories, it uses each repository root for repo-specific work, or their common workspace root when the knowledge should be shared. A root without Git keeps its ledger in `.memory`.

## Storage, privacy, and behavior

Each MCP tool call receives a project path and resolves storage itself. It uses the Git common metadata directory when `<project>/.git` exists, so linked worktrees share memory and ordinary Git add and commit operations cannot include the database. Without Git it uses `<project>/.memory/memory.sqlite`.

Storage is resolved independently for each tool call from its required absolute `project_path`. That path defines the memory boundary; it may be one repository or a shared workspace. Paths passed to `get_file_context.paths` and `record_memory.applies_to` are normalized relative to that root and used for matching, not filesystem lookups.

The database is local but not encrypted. Any user or process that can read its path can read it. Backups or copies containing Git metadata or `.memory` may also contain the ledger.

The MCP server provides five tools:

- `get_file_context(project_path, paths)`: retrieve active knowledge attached to files or parent directories.
- `search_memory(project_path, ...)`: search active or historical records using tags, a phrase, or both.
- `record_memory(project_path, ...)`: add broad knowledge or rules scoped to an `applies_to` list.
- `supersede_memory(project_path, ...)`: retire an obsolete record while preserving history.
- `dispute_memory(project_path, ...)`: flag unresolved conflicting knowledge.

`applies_to` is a list of project-relative files or directories governed by a record. File lookup accepts several paths in one call, normalizes separators, and returns records whose scopes match an exact path or one of its parent directories. A rule spanning separate packages lists each governed file or directory; an empty `applies_to` means genuinely broad project or domain knowledge, not merely multi-package scope.

Agents use both retrieval paths during development: `search_memory` recalls broad decisions using task language, while `get_file_context` retrieves rules for the intended or touched files. Recording mirrors that split. Before saving a scoped rule, inspect the instances it claims to govern to verify the scope and preserve real exceptions. Habitual corrections such as “we usually,” “we tend to,” “always,” and “never” are strong signals to record immediately when they express a durable convention.

Search is lexical SQLite FTS5 with BM25 ranking across titles, content, sources, and tags. It accepts one to three exact tag phrases, a free-text phrase whose terms are matched broadly, or both; matches are combined with OR. Tags describe a future task that should retrieve the knowledge—for example, `add response field` rather than only `mappers`. There are no embeddings, vector search, automatic code indexing, or project scanning.

## Limitations and ideas

Current limitations:

- Lexical search can miss synonyms and conceptual matches.
- There is no record editing, deletion command, or automatic deduplication.
- The server does not verify an agent's claims or whether a user really confirmed one.
- MCP instructions guide a client but cannot force it to retrieve or record memory.
- Separate processes rely on normal SQLite locking and may briefly contend.
- The local database is not an encryption or access-control boundary.
- ContextLedger is designed for modest local workloads, not a multi-user service.

Possible next work:

- [ ] Measure retrieval misses before considering semantic or vector search.
- [ ] Add provenance-preserving merge and deduplication assistance.
- [ ] Add concurrency and busy-timeout tests.
- [ ] Test packaged MCP integrations end to end in CI.
- [ ] Add a local browser/export workflow for records.
- [ ] Evaluate practical optional encryption at rest.
- [ ] Publish a signed, versioned Python package when release demand warrants it.

## Development

Development requires [uv](https://docs.astral.sh/uv/):

```sh
git clone <repository-url>
cd context-ledger-mcp
uv sync --extra test
uv run pytest -q
uv run context-ledger status
```

Tests create temporary projects and do not write ledger data into this project.

Run the development checkout as an MCP server:

```sh
uv run context-ledger serve
```

The implementation is intentionally small:

```text
src/context_ledger/cli.py       command-line interface
src/context_ledger/ledger.py    SQLite records, search, and lifecycle
src/context_ledger/paths.py     Project and database paths
src/context_ledger/server.py    MCP server and tools
src/context_ledger/prompts/     server and harness instructions
tests/                          CLI, storage, paths, prompts, and MCP tests
```
