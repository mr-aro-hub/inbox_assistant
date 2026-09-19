# Business Requirements Document

## Problem and users

Knowledge workers lose time finding urgent mail, translating vague deadlines into actions, and writing replies that accidentally make commitments. The assistant helps an individual triage an inbox, ask grounded questions, prepare a reply, and export confirmed dates. It is a decision-support tool: it never sends email or writes to a calendar account.

## Success criteria

- A user can identify urgent/high-priority mail and the model's reason for that label.
- Every generated answer exposes its supporting email records; unsupported answers say so.
- Replies involving commitments, pricing, scheduling, or sensitive content are visibly marked for human review.
- Only concrete, source-backed dates become calendar events.
- Results remain available after a local app restart without re-running the model.

## Functional requirements

1. Load the bundled inbox into a local SQLite database and retain generated analyses, drafts, and calendar plans.
2. Produce schema-validated summary, priority, tasks, sentiment, and reply tone.
3. Draft, but never send, a reply and surface a confidence/review gate.
4. Answer inbox questions only from supplied mail and return valid source IDs.
5. Export usable events as RFC 5545 `.ics` data.

## Non-functional requirements and constraints

- Consent is required before any AI action. Email addresses and phone numbers are redacted before a Gemini request.
- API keys reside in `.env`, never in source control. Data is local to `data/inbox.db`.
- Invalid model JSON, missing API configuration, malformed dates, and missing consent must fail safely without producing an action.
- The demonstration uses mock mail; live Gmail/Outlook ingestion is intentionally out of scope.
