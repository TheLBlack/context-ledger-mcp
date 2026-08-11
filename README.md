# ContextLedger

Local, explicitly scoped memory for coding agents.

ContextLedger lets an agent keep useful project knowledge between sessions: architectural decisions, code observations, durable documentation, and failed approaches worth avoiding. It stores conclusions, not chat transcripts.

Many agent-memory products assume organization-wide adoption, cloud infrastructure, or a new company policy. ContextLedger is for the developer who wants durable agent memory today: install it locally, enable it only for the repositories you choose, and keep the data in those repositories' private Git metadata. No cloud deployment, subscription, external account, or company-wide rollout is required.

It is harness- and model-agnostic. ContextLedger exposes standard [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tools over stdio, so any MCP client can use it. Codex and Claude Code are included below as concrete setup examples, not privileged integrations. By default, each repository has an isolated SQLite database under its private Git metadata:

```text
<repository>/.git/llm-memory/memory.sqlite
```

There is no account, cloud service, telemetry, network server, global index, or required team rollout. Linked Git worktrees share a ledger because they share a Git common directory. An explicit database path can instead give a directory, workspace, or selected group of repositories one shared ledger.

## Quick start

Requirements: Python 3.11 or newer, Git, SQLite with FTS5, and [uv](https://docs.astral.sh/uv/). Normal Python distributions include FTS5.

### 1. Install

From a clone of ContextLedger:

```sh
uv tool install .
command -v context-ledger
context-ledger --help
```

`command -v context-ledger` must print the installed executable file, for example `/Users/alice/.local/bin/context-ledger`. On Windows, use `where context-ledger`. If the command is missing, run `uv tool update-shell`, restart the shell, and repeat the block.

### 2. Add it to an MCP client

ContextLedger uses MCP over standard input/output. The following client-specific commands all configure the same executable and arguments, binding one server process to the current repository.

#### Claude Code

Run this complete block inside the target repository:

`LEDGER_DB` controls where the database file is stored; it points to the repository's private Git metadata by default, so change that variable in the block if you want another location.

```sh
(
set -eu
LEDGER_BIN="$(command -v context-ledger)"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
GIT_COMMON_DIR="$(git -C "$PROJECT_ROOT" rev-parse --path-format=absolute --git-common-dir)"
LEDGER_DB="$GIT_COMMON_DIR/llm-memory/memory.sqlite"
test -x "$LEDGER_BIN"
test -d "$GIT_COMMON_DIR"
claude mcp add --transport stdio --scope local context-ledger -- \
  "$LEDGER_BIN" serve --database "$LEDGER_DB"
claude mcp get context-ledger

INSTRUCTIONS_FILE="$HOME/.claude/CLAUDE.md"
mkdir -p "$(dirname "$INSTRUCTIONS_FILE")"
if ! grep -Fq "When Context Ledger MCP tools are available" "$INSTRUCTIONS_FILE" 2>/dev/null; then
  echo >> "$INSTRUCTIONS_FILE"
  context-ledger snippet >> "$INSTRUCTIONS_FILE"
fi
)
```

The second half appends the ContextLedger snippet to Claude Code's default personal instruction file, `~/.claude/CLAUDE.md`. The `if` check prevents duplicates when the block is run again. For project-only instructions, set `INSTRUCTIONS_FILE="$PROJECT_ROOT/CLAUDE.md"`; otherwise change it if your personal file lives elsewhere. Start a new Claude Code session and run `/mcp` to check the connection. See the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).

#### Codex

Run this complete block inside the target repository:

`LEDGER_DB` controls where the database file is stored; it points to the repository's private Git metadata by default, so change that variable in the block if you want another location.

```sh
(
set -eu
LEDGER_BIN="$(command -v context-ledger)"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
GIT_COMMON_DIR="$(git -C "$PROJECT_ROOT" rev-parse --path-format=absolute --git-common-dir)"
LEDGER_DB="$GIT_COMMON_DIR/llm-memory/memory.sqlite"
test -x "$LEDGER_BIN"
test -d "$GIT_COMMON_DIR"
codex mcp add context-ledger -- \
  "$LEDGER_BIN" serve --database "$LEDGER_DB"
codex mcp list

INSTRUCTIONS_FILE="$HOME/.codex/AGENTS.md"
mkdir -p "$(dirname "$INSTRUCTIONS_FILE")"
if ! grep -Fq "When Context Ledger MCP tools are available" "$INSTRUCTIONS_FILE" 2>/dev/null; then
  echo >> "$INSTRUCTIONS_FILE"
  context-ledger snippet >> "$INSTRUCTIONS_FILE"
fi
)
```

The second half appends the ContextLedger snippet to Codex's default personal instruction file, `~/.codex/AGENTS.md`. The `if` check prevents duplicates when the block is run again. For project-only instructions, set `INSTRUCTIONS_FILE="$PROJECT_ROOT/AGENTS.md"`; otherwise change it if your personal file lives elsewhere. Start a new Codex session and run `/mcp` to check the connection. See the [Codex MCP documentation](https://developers.openai.com/codex/mcp).

#### Generic MCP client

If the client has no dedicated setup command, add the equivalent stdio server object in its MCP configuration:

```json
{
  "mcpServers": {
    "context-ledger": {
      "command": "/absolute/path/printed/by/command-v/context-ledger",
      "args": ["serve", "--database", "/absolute/path/to/your/project/.git/llm-memory/memory.sqlite"]
    }
  }
}
```

Use the exact output of `command -v context-ledger` for `command`. Get the correct default database path with `git rev-parse --path-format=absolute --git-common-dir`, then append `/llm-memory/memory.sqlite`. The outer property names vary by client; the stdio command and arguments do not.

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
/absolute/path/to/context-ledger status --database /absolute/path/to/memory.sqlite
```

Do not test `serve` directly. It waits silently for MCP messages on standard input.

## CLI reference

Commands use the Git repository containing the current directory by default. Add `--repository PATH` to target another repository, or `--database PATH` to select any standalone or shared SQLite ledger. The two options are mutually exclusive.

```sh
# Create the database and print its path
context-ledger init

# Show the repository, database path, and active counts
context-ledger status

# List records
context-ledger list
context-ledger list --kind decision --limit 50
context-ledger list --all

# Inspect or search records
context-ledger inspect 1
context-ledger search "SQLite storage"
context-ledger search --kind failed_attempt --all "old approach"

# Record durable knowledge
context-ledger record decision \
  "Database choice" \
  "Use SQLite with FTS5; no embeddings initially" \
  --authority user_confirmed \
  --source "architecture discussion"

# Preserve lifecycle history
context-ledger supersede 1 --replacement 2
context-ledger dispute 3

# Inspect packaged instructions
context-ledger snippet
context-ledger snippet --path
context-ledger prompt
context-ledger prompt --path

# Start the MCP stdio server
context-ledger serve
```

Record kinds are `decision`, `observation`, `documentation`, and `failed_attempt`. Evidence authorities are `user_confirmed`, `code_observed`, and `agent_inferred`. Authority describes the source of a claim, not confidence in it.

Command results are JSON except for `init`, `prompt`, and `snippet`.

## Multiple projects and shared ledgers

Install ContextLedger once. Give repositories separate database paths for isolation:

```text
one ContextLedger installation
├── project A process → project-a/.git/llm-memory/memory.sqlite
└── project B process → project-b/.git/llm-memory/memory.sqlite
```

Processes communicate through separate stdin/stdout streams. They do not use ports or share global state and remain idle between calls.

For a client session that opens more than one repository:

```json
{
  "mcpServers": {
    "ledger-project-a": {
      "command": "/absolute/path/to/context-ledger",
      "args": ["serve", "--database", "/projects/project-a/.git/llm-memory/memory.sqlite"]
    },
    "ledger-project-b": {
      "command": "/absolute/path/to/context-ledger",
      "args": ["serve", "--database", "/projects/project-b/.git/llm-memory/memory.sqlite"]
    }
  }
}
```

Each process is bound to one database. To share memory across a workspace or a selected group of repositories, point their MCP connections at the same path:

```json
{
  "mcpServers": {
    "context-ledger": {
      "command": "/absolute/path/to/context-ledger",
      "args": ["serve", "--database", "/projects/product/.context-ledger/memory.sqlite"]
    }
  }
}
```

The containing directory does not need to be a Git repository. Every connection using that path reads and writes the same ledger. Use separate paths where isolation matters.

## Storage, privacy, and behavior

Without an explicit database, ContextLedger asks Git for its common metadata directory and stores SQLite below it. The Quick Start passes that same path explicitly at the MCP connection level. Ordinary Git add and commit operations cannot include a database inside Git metadata.

The database is local but not encrypted. Any user or process that can read its path can read it. Backups or copies containing Git metadata or an explicitly selected shared path may also contain the ledger.

The MCP server provides five tools:

- `get_project_context`: retrieve active knowledge relevant to a task.
- `search_memory`: search active or historical records.
- `record_memory`: add a durable conclusion.
- `supersede_memory`: retire an obsolete record while preserving history.
- `dispute_memory`: flag unresolved conflicting knowledge.

Search is lexical SQLite FTS5 with BM25 ranking. There are no embeddings, vector search, automatic code indexing, or repository scanning.

## Limitations and ideas

Current limitations:

- Lexical search can miss synonyms and conceptual matches.
- There is no record editing, deletion command, migration UI, or automatic deduplication.
- The server does not verify an agent's claims or whether a user really confirmed one.
- MCP instructions guide a client but cannot force it to retrieve or record memory.
- Separate processes rely on normal SQLite locking and may briefly contend.
- Schema changes do not yet have a versioned migration system.
- The local database is not an encryption or access-control boundary.
- ContextLedger is designed for modest local workloads, not a multi-user service.

Possible next work:

- [ ] Add schema versioning and tested migrations.
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

The final status command expects the checkout to be a Git repository. Tests create temporary repositories and do not write ledger data into this project.

Run the development checkout as an MCP server:

```sh
uv run context-ledger serve --repository /absolute/path/to/project
```

The implementation is intentionally small:

```text
src/context_ledger/cli.py       command-line interface
src/context_ledger/ledger.py    SQLite records, search, and lifecycle
src/context_ledger/paths.py     Git repository and database paths
src/context_ledger/server.py    MCP server and tools
src/context_ledger/prompts/     server and harness instructions
tests/                          CLI, storage, paths, prompts, and MCP tests
```
