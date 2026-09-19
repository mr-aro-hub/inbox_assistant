"""SQLite persistence for local demo data and generated assistant artefacts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from schemas import CalendarPlan, DraftReply, Email, EmailAnalysis

T = TypeVar("T", bound=BaseModel)


class InboxRepository:
    """A deliberately small local repository; SQLite needs no server or credentials."""

    def __init__(self, database_path: str | Path = "data/inbox.db") -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS emails (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS artefacts (
                    email_id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY (email_id, kind),
                    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
                );
                """
            )

    def seed_emails(self, emails: list[Email]) -> list[Email]:
        """Insert bundled sample emails once; never overwrite a user's local record."""
        with self._connect() as connection:
            connection.executemany(
                "INSERT OR IGNORE INTO emails(id, payload) VALUES (?, ?)",
                [(email.id, email.model_dump_json()) for email in emails],
            )
        return self.list_emails()

    def list_emails(self) -> list[Email]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM emails ORDER BY id").fetchall()
        return [Email.model_validate_json(row["payload"]) for row in rows]

    def save(self, email_id: str, kind: str, model: BaseModel) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO artefacts(email_id, kind, payload) VALUES (?, ?, ?) "
                "ON CONFLICT(email_id, kind) DO UPDATE SET payload = excluded.payload",
                (email_id, kind, model.model_dump_json()),
            )

    def load(self, email_id: str, kind: str, model_type: type[T]) -> T | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM artefacts WHERE email_id = ? AND kind = ?",
                (email_id, kind),
            ).fetchone()
        return model_type.model_validate_json(row["payload"]) if row else None

    def clear(self, email_id: str, kind: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM artefacts WHERE email_id = ? AND kind = ?", (email_id, kind))


ARTEFACT_TYPES = {
    "analysis": EmailAnalysis,
    "draft": DraftReply,
    "calendar": CalendarPlan,
}
