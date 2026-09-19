"""SQLite persistence and data access for the Inbox Assistant.

The application is deliberately single-user, so SQLite provides durable relational
storage without a database server, credentials, or a new runtime dependency.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from schemas import CalendarEvent, CalendarPlan, DraftReply, Email, EmailAnalysis, Task


class InboxRepository:
    """Owns the application's relational schema and all database access."""

    def __init__(self, database_path: str | Path = "data/inbox.db") -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _create_schema(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS emails (
                    id TEXT PRIMARY KEY,
                    sender_name TEXT NOT NULL,
                    sender_email TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    thread_id TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_emails_received_at ON emails(received_at DESC);
                CREATE INDEX IF NOT EXISTS idx_emails_thread_id ON emails(thread_id);

                CREATE TABLE IF NOT EXISTS analyses (
                    email_id TEXT PRIMARY KEY REFERENCES emails(id) ON DELETE CASCADE,
                    summary TEXT NOT NULL,
                    priority TEXT NOT NULL CHECK(priority IN ('Urgent', 'High', 'Normal', 'Low')),
                    priority_reason TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    suggested_tone TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_analyses_priority ON analyses(priority);

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
                    description TEXT NOT NULL,
                    deadline TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_email_id ON tasks(email_id);

                CREATE TABLE IF NOT EXISTS reply_drafts (
                    email_id TEXT PRIMARY KEY REFERENCES emails(id) ON DELETE CASCADE,
                    reply_text TEXT NOT NULL,
                    confidence TEXT NOT NULL CHECK(confidence IN ('High', 'Medium', 'Low')),
                    confidence_reason TEXT NOT NULL,
                    needs_human_review INTEGER NOT NULL CHECK(needs_human_review IN (0, 1)),
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    starts_at TEXT NOT NULL,
                    ends_at TEXT NOT NULL,
                    all_day INTEGER NOT NULL CHECK(all_day IN (0, 1)),
                    source TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_calendar_events_email_id ON calendar_events(email_id);
                """
            )

    def seed_emails(self, emails: list[Email]) -> list[Email]:
        """Load bundled demo mail once; existing local records are never overwritten."""
        with self._connection() as connection:
            connection.executemany(
                """INSERT OR IGNORE INTO emails
                (id, sender_name, sender_email, subject, body, received_at, thread_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (email.id, email.sender_name, email.sender_email, email.subject,
                     email.body, email.timestamp, email.thread_id)
                    for email in emails
                ],
            )
        return self.list_emails()

    def list_emails(self) -> list[Email]:
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM emails ORDER BY received_at DESC").fetchall()
        return [
            Email(id=row["id"], sender_name=row["sender_name"], sender_email=row["sender_email"],
                  subject=row["subject"], body=row["body"], timestamp=row["received_at"],
                  thread_id=row["thread_id"])
            for row in rows
        ]

    def save_analysis(self, email_id: str, analysis: EmailAnalysis) -> None:
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO analyses(email_id, summary, priority, priority_reason, sentiment, suggested_tone)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(email_id) DO UPDATE SET summary=excluded.summary, priority=excluded.priority,
                priority_reason=excluded.priority_reason, sentiment=excluded.sentiment,
                suggested_tone=excluded.suggested_tone, updated_at=CURRENT_TIMESTAMP""",
                (email_id, analysis.summary, analysis.priority, analysis.priority_reason,
                 analysis.sentiment, analysis.suggested_tone),
            )
            connection.execute("DELETE FROM tasks WHERE email_id = ?", (email_id,))
            connection.executemany(
                "INSERT INTO tasks(email_id, description, deadline) VALUES (?, ?, ?)",
                [(email_id, task.description, task.deadline) for task in analysis.tasks],
            )

    def get_analysis(self, email_id: str) -> EmailAnalysis | None:
        with self._connection() as connection:
            analysis = connection.execute("SELECT * FROM analyses WHERE email_id = ?", (email_id,)).fetchone()
            tasks = connection.execute("SELECT description, deadline FROM tasks WHERE email_id = ? ORDER BY id", (email_id,)).fetchall()
        if analysis is None:
            return None
        return EmailAnalysis(summary=analysis["summary"], priority=analysis["priority"],
            priority_reason=analysis["priority_reason"], sentiment=analysis["sentiment"],
            suggested_tone=analysis["suggested_tone"],
            tasks=[Task(description=task["description"], deadline=task["deadline"]) for task in tasks])

    def save_draft(self, email_id: str, draft: DraftReply) -> None:
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO reply_drafts(email_id, reply_text, confidence, confidence_reason, needs_human_review)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(email_id) DO UPDATE SET reply_text=excluded.reply_text,
                confidence=excluded.confidence, confidence_reason=excluded.confidence_reason,
                needs_human_review=excluded.needs_human_review, updated_at=CURRENT_TIMESTAMP""",
                (email_id, draft.reply_text, draft.confidence, draft.confidence_reason, int(draft.needs_human_review)),
            )

    def get_draft(self, email_id: str) -> DraftReply | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM reply_drafts WHERE email_id = ?", (email_id,)).fetchone()
        return None if row is None else DraftReply(reply_text=row["reply_text"], confidence=row["confidence"],
            confidence_reason=row["confidence_reason"], needs_human_review=bool(row["needs_human_review"]))

    def save_calendar_plan(self, email_id: str, plan: CalendarPlan) -> None:
        with self._connection() as connection:
            connection.execute("DELETE FROM calendar_events WHERE email_id = ?", (email_id,))
            connection.executemany(
                """INSERT INTO calendar_events(email_id, title, starts_at, ends_at, all_day, source)
                VALUES (?, ?, ?, ?, ?, ?)""",
                [(email_id, event.title, event.start, event.end, int(event.all_day), event.source) for event in plan.events],
            )

    def get_calendar_plan(self, email_id: str) -> CalendarPlan | None:
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM calendar_events WHERE email_id = ? ORDER BY starts_at", (email_id,)).fetchall()
        if not rows:
            return None
        return CalendarPlan(events=[CalendarEvent(title=row["title"], start=row["starts_at"], end=row["ends_at"],
            all_day=bool(row["all_day"]), source=row["source"]) for row in rows])
