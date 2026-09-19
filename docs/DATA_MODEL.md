# Data model

SQLite is the local system of record. It is selected for the single-user Streamlit
deployment because it is transactional, relational, and needs no server process.

```text
emails (1) ──< analyses (1)
   │  \────< tasks (0..n)
   ├──────< reply_drafts (0..1)
   └──────< calendar_events (0..n)
```

| Entity | Key fields | Purpose |
| --- | --- | --- |
| `emails` | `id`, sender, subject, body, `received_at`, `thread_id` | Inbox source records. |
| `analyses` | `email_id`, priority, sentiment, summary | One current LLM analysis for an email. |
| `tasks` | `id`, `email_id`, deadline | Normalized action items from an analysis. |
| `reply_drafts` | `email_id`, confidence, review flag | One latest suggested reply per email. |
| `calendar_events` | `id`, `email_id`, start/end, all-day | Zero or more schedulable results per email. |

Foreign keys use `ON DELETE CASCADE`; indexes support inbox recency, thread lookup,
priority reporting, and child-record retrieval. The repository uses upserts for the
one-to-one generated entities and replace semantics for task/event collections.
