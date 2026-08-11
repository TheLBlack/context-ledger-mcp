from __future__ import annotations

import argparse
import json
import sys
from importlib.resources import as_file, files
from pathlib import Path
from typing import Sequence

from .ledger import AUTHORITIES, KINDS, Ledger, LedgerRecord
from .paths import find_repository_root, resolve_database_path
from .server import create_server, load_harness_snippet, load_instructions


def _add_storage(parser: argparse.ArgumentParser) -> None:
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument(
        "--repository",
        type=Path,
        help="target Git repository (defaults to the repository containing the current directory)",
    )
    storage.add_argument(
        "--database",
        type=Path,
        help="use this SQLite database instead of deriving one from Git metadata",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="context-ledger", description="Explicitly scoped memory for coding agents")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="run the MCP server over stdio")
    _add_storage(serve)

    init = subparsers.add_parser("init", help="create and report the repository's private ledger database")
    _add_storage(init)

    status = subparsers.add_parser("status", help="show storage location and active record counts")
    _add_storage(status)

    list_parser = subparsers.add_parser("list", help="list recent records")
    _add_storage(list_parser)
    list_parser.add_argument("--kind", choices=sorted(KINDS))
    list_parser.add_argument("--all", action="store_true", help="include superseded and disputed records")
    list_parser.add_argument("--limit", type=int, default=20)

    inspect = subparsers.add_parser("inspect", help="show one record by id")
    _add_storage(inspect)
    inspect.add_argument("record_id", type=int)

    search = subparsers.add_parser("search", help="search record titles, content, and sources")
    _add_storage(search)
    search.add_argument("query")
    search.add_argument("--kind", choices=sorted(KINDS))
    search.add_argument("--all", action="store_true", help="include superseded and disputed records")
    search.add_argument("--limit", type=int, default=10)

    record = subparsers.add_parser("record", help="record a durable project conclusion")
    _add_storage(record)
    record.add_argument("kind", choices=sorted(KINDS))
    record.add_argument("title")
    record.add_argument("content")
    record.add_argument("--authority", choices=sorted(AUTHORITIES), required=True)
    record.add_argument("--source")

    supersede = subparsers.add_parser("supersede", help="mark a record obsolete")
    _add_storage(supersede)
    supersede.add_argument("record_id", type=int)
    supersede.add_argument("--replacement", type=int)

    dispute = subparsers.add_parser("dispute", help="mark a record disputed")
    _add_storage(dispute)
    dispute.add_argument("record_id", type=int)

    prompt = subparsers.add_parser("prompt", help="print the exact instructions used by the MCP server")
    prompt.add_argument("--path", action="store_true", help="print the source/package file path instead of its content")

    snippet = subparsers.add_parser("snippet", help="print the short AGENTS.md/CLAUDE.md integration snippet")
    snippet.add_argument("--path", action="store_true", help="print the source/package file path instead of its content")
    return parser


def _json(value: LedgerRecord | list[LedgerRecord] | dict[str, object]) -> None:
    if isinstance(value, list):
        payload: object = [record.to_dict() for record in value]
    elif isinstance(value, LedgerRecord):
        payload = value.to_dict()
    else:
        payload = value
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _ledger(repository: Path | None, database: Path | None) -> Ledger:
    return Ledger(resolve_database_path(repository, database))


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"prompt", "snippet"}:
        filename = "server_instructions.md" if args.command == "prompt" else "harness_snippet.md"
        resource = files("context_ledger.prompts").joinpath(filename)
        if args.path:
            with as_file(resource) as path:
                print(path)
        else:
            content = load_instructions() if args.command == "prompt" else load_harness_snippet()
            print(content, end="")
        return 0

    try:
        if args.command == "serve":
            create_server(args.repository, args.database).run(transport="stdio")
            return 0
        if args.command == "init":
            with _ledger(args.repository, args.database) as ledger:
                print(ledger.path)
            return 0
        if args.command == "status":
            with _ledger(args.repository, args.database) as ledger:
                payload: dict[str, object] = {
                    "database": str(ledger.path),
                    "active_records": ledger.counts(),
                }
                if args.database is None:
                    payload["repository"] = str(find_repository_root(args.repository))
                _json(payload)
            return 0
        with _ledger(args.repository, args.database) as ledger:
            if args.command == "list":
                _json(ledger.list_records(kind=args.kind, include_inactive=args.all, limit=args.limit))
            elif args.command == "inspect":
                _json(ledger.get(args.record_id))
            elif args.command == "search":
                _json(ledger.search(args.query, kind=args.kind, include_inactive=args.all, limit=args.limit))
            elif args.command == "record":
                _json(ledger.record(args.kind, args.title, args.content, args.authority, args.source))
            elif args.command == "supersede":
                _json(ledger.supersede(args.record_id, args.replacement))
            elif args.command == "dispute":
                _json(ledger.dispute(args.record_id))
        return 0
    except (KeyError, RuntimeError, ValueError) as error:
        print(f"context-ledger: {error}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
