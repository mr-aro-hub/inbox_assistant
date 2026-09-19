# High-Level Design

```text
JSON sample mail -> InboxRepository (SQLite) -> Streamlit UI
                                           |       |
                                           |       +-> local cached artefacts
                                           v
privacy redaction + consent -> Gemini structured output -> Pydantic validation
                                                        -> SQLite / UI / ICS export
```

`main.py` owns interaction flow. `storage.py` contains the persistence boundary: `emails` stores immutable JSON records and `artefacts` stores versionable generated output keyed by email and type. SQLite was selected for a zero-configuration, single-user hackathon deployment; a managed relational database can replace this repository for multi-user deployment.

`llm_logic.py` owns every provider call and asks Gemini for Pydantic-constrained JSON. `privacy.py` is the outbound data boundary: it removes email addresses and phone numbers. The UI adds a consent gate, and no send or calendar-write integration exists. `calendar_export.py` is isolated, deterministic, and serializes RFC 5545-compatible CRLF/folded `.ics` content.

For scale, queue analysis jobs, add per-user authentication/row-level authorization, encrypt database storage, use retrieval over indexed mail rather than putting an entire inbox in one prompt, and add provider rate limiting/retries with observable audit events.
