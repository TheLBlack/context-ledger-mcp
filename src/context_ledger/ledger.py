from __future__ import annotations

import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

RecordKind = Literal["decision", "observation", "documentation", "failed_attempt"]
Authority = Literal["user_confirmed", "code_observed", "agent_inferred"]
Lifecycle = Literal["active", "superseded", "disputed"]

KINDS = frozenset(("decision", "observation", "documentation", "failed_attempt"))
AUTHORITIES = frozenset(("user_confirmed", "code_observed", "agent_inferred"))
LIFECYCLES = frozenset(("active", "superseded", "disputed"))


def _tag_phrases(tags: list[str]) -> list[str]:
    phrases: list[str] = []
    for tag in tags:
        terms = re.findall(r"[\w-]+", tag, flags=re.UNICODE)
        if terms:
            phrases.append(" ".join(terms).lower())
    phrases = list(dict.fromkeys(phrases))
    if not phrases:
        raise ValueError("tags must contain searchable text")
    if len(phrases) > 3:
        raise ValueError("at most 3 tags are allowed")
    return phrases


def _fts_query(tags: list[str] | None, phrase: str | None) -> str:
    """Build a query from exact tag phrases and broad free-text terms."""
    parts = [f'"{tag}"' for tag in _tag_phrases(tags)] if tags else []
    if phrase is not None:
        parts.extend(f'"{term}"' for term in re.findall(r"[\w-]+", phrase, flags=re.UNICODE))
    if not parts:
        raise ValueError("provide at least one tag or a searchable phrase")
    return " OR ".join(dict.fromkeys(parts))


@dataclass(frozen=True)
class LedgerRecord:
    id: int
    kind: str
    title: str
    content: str
    authority: str
    status: str
    source: str | None
    applies_to: str | None
    tags: str | None
    created_at: str
    superseded_by: int | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK(kind IN ('decision','observation','documentation','failed_attempt')),
    title TEXT NOT NULL CHECK(length(trim(title)) > 0),
    content TEXT NOT NULL CHECK(length(trim(content)) > 0),
    authority TEXT NOT NULL CHECK(authority IN ('user_confirmed','code_observed','agent_inferred')),
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','superseded','disputed')),
    source TEXT,
    applies_to TEXT,
    tags TEXT,
    created_at TEXT NOT NULL,
    superseded_by INTEGER REFERENCES records(id)
);
"""

SEARCH_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(
    title, content, source, tags, content='records', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS records_ai AFTER INSERT ON records BEGIN
    INSERT INTO records_fts(rowid, title, content, source, tags)
    VALUES (new.id, new.title, new.content, new.source, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS records_ad AFTER DELETE ON records BEGIN
    INSERT INTO records_fts(records_fts, rowid, title, content, source, tags)
    VALUES ('delete', old.id, old.title, old.content, old.source, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS records_au AFTER UPDATE ON records BEGIN
    INSERT INTO records_fts(records_fts, rowid, title, content, source, tags)
    VALUES ('delete', old.id, old.title, old.content, old.source, old.tags);
    INSERT INTO records_fts(rowid, title, content, source, tags)
    VALUES (new.id, new.title, new.content, new.source, new.tags);
END;
"""


def _normalize_scope(path: str) -> str:
    """Normalize a project-relative file or directory scope."""
    value = path.strip().replace("\\", "/")
    if not value:
        raise ValueError("applies_to paths must not be empty")
    while "//" in value:
        value = value.replace("//", "/")
    if value.startswith("./"):
        value = value[2:]
    value = value.rstrip("/") or "."
    if value.startswith("/") or re.match(r"^[A-Za-z]:/", value) or value == ".." or value.startswith("../") or "/../" in value:
        raise ValueError("applies_to paths must be project-relative and must not contain '..'")
    return value


class Ledger:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self.connection.executescript(SEARCH_SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Ledger":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _record(row: sqlite3.Row) -> LedgerRecord:
        return LedgerRecord(**dict(row))

    def record(
        self,
        kind: RecordKind,
        title: str,
        content: str,
        authority: Authority,
        source: str | None = None,
        applies_to: str | None = None,
        tags: list[str] | None = None,
    ) -> LedgerRecord:
        if kind not in KINDS:
            raise ValueError(f"Invalid kind: {kind}")
        if authority not in AUTHORITIES:
            raise ValueError(f"Invalid authority: {authority}")
        if not title.strip() or not content.strip():
            raise ValueError("title and content must not be empty")
        scope = _normalize_scope(applies_to) if applies_to is not None else None
        compact_tags = ", ".join(_tag_phrases(tags)) if tags is not None else None
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.connection.execute(
            """INSERT INTO records(kind,title,content,authority,source,applies_to,tags,created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (kind, title.strip(), content.strip(), authority, source, scope, compact_tags, now),
        )
        self.connection.commit()
        return self.get(cursor.lastrowid)

    def get(self, record_id: int) -> LedgerRecord:
        row = self.connection.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
        if row is None:
            raise KeyError(f"No record with id {record_id}")
        return self._record(row)

    def list_records(self, *, include_inactive: bool = False, limit: int = 20) -> list[LedgerRecord]:
        clauses: list[str] = []
        params: list[object] = []
        if not include_inactive:
            clauses.append("status = 'active'")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(limit, 100)))
        rows = self.connection.execute(
            f"SELECT * FROM records {where} ORDER BY id DESC LIMIT ?", params
        ).fetchall()
        return [self._record(row) for row in rows]

    def counts(self) -> dict[str, int]:
        result = {kind: 0 for kind in sorted(KINDS)}
        for row in self.connection.execute(
            "SELECT kind, count(*) AS count FROM records WHERE status='active' GROUP BY kind"
        ):
            result[row["kind"]] = row["count"]
        return result

    def search(
        self,
        tags: list[str] | None = None,
        phrase: str | None = None,
        *,
        include_inactive: bool = False,
        limit: int = 10,
    ) -> list[LedgerRecord]:
        clauses = ["records_fts MATCH ?"]
        params: list[object] = [_fts_query(tags, phrase)]
        if not include_inactive:
            clauses.append("r.status = 'active'")
        params.append(max(1, min(limit, 100)))
        rows = self.connection.execute(
            f"""SELECT r.* FROM records_fts f JOIN records r ON r.id=f.rowid
                WHERE {' AND '.join(clauses)} ORDER BY bm25(records_fts), r.id DESC LIMIT ?""",
            params,
        ).fetchall()
        return [self._record(row) for row in rows]

    def file_context(self, paths: list[str], *, limit: int = 20) -> list[LedgerRecord]:
        """Return active rules scoped to each file or any of its parent directories."""
        normalized = list(dict.fromkeys(_normalize_scope(path) for path in paths))
        if not normalized:
            raise ValueError("paths must contain at least one project-relative path")
        matches: list[LedgerRecord] = []
        seen: set[int] = set()
        rows = self.connection.execute(
            "SELECT * FROM records WHERE status='active' AND applies_to IS NOT NULL ORDER BY id DESC"
        ).fetchall()
        for row in rows:
            record = self._record(row)
            scope = record.applies_to
            if scope is not None and any(
                scope == "." or path == scope or path.startswith(f"{scope}/") for path in normalized
            ):
                if record.id not in seen:
                    matches.append(record)
                    seen.add(record.id)
        matches.sort(key=lambda item: (len(item.applies_to or ""), item.id), reverse=True)
        return matches[: max(1, min(limit, 100))]

    def supersede(self, record_id: int, replacement_id: int | None = None) -> LedgerRecord:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            old = self.get(record_id)
            if old.status == "superseded":
                raise ValueError(f"Record {record_id} is already {old.status}")
            if replacement_id is not None:
                replacement = self.get(replacement_id)
                if replacement.id == old.id:
                    raise ValueError("A record cannot supersede itself")
                if replacement.kind != old.kind:
                    raise ValueError("Replacement must have the same kind")
                if replacement.status != "active":
                    raise ValueError("Replacement must be active")
            self.connection.execute(
                "UPDATE records SET status='superseded', superseded_by=? WHERE id=?",
                (replacement_id, record_id),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return self.get(record_id)

    def dispute(self, record_id: int) -> LedgerRecord:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            record = self.get(record_id)
            if record.status != "active":
                raise ValueError(f"Record {record_id} is already {record.status}")
            self.connection.execute("UPDATE records SET status='disputed' WHERE id=?", (record_id,))
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return self.get(record_id)
