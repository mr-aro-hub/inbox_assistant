# AI Email Inbox Assistant

## Setup 

```bash
cd inbox-assistant
python -m venv .venv
source .venv/bin/activate     # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # Windows PowerShell: copy .env.example .env
# then edit .env and paste your Gemini API key (get one free at aistudio.google.com)
```

Run the app:
```bash
streamlit run main.py
```

**Don't commit or share the venv.** Create your own locally — a venv built on one
machine hardcodes that machine's Python path in `pyvenv.cfg` and breaks for
everyone else. If you see `did not find executable at '...python.exe'`, delete the
venv directory and rebuild it with the steps above.

## What's already built

- `schemas.py` — Pydantic models for emails and LLM output (analysis + draft reply)
- `llm_logic.py` — Gemini API calls, structured JSON output, three functions:
  `analyze_email()`, `draft_reply()`, and `answer_inbox_question()`
- `data/emails.json` — 8 realistic mock emails (urgent outage, contract pricing,
  frustrated client, newsletter, scheduling confirmation, budget request) covering
  a good spread for demoing
- `main.py` — working Streamlit app: **Ask My Inbox** search, inbox list, email
  detail view, analysis panel, draft reply with confidence scoring, and an
  **Inbox Health Score** in the sidebar
- `calendar_export.py` — turns planned events into a downloadable `.ics`.
  Stdlib only, no calendar account or API involved
- `ui.py` — the stylesheet and the HTML builders `main.py` renders. Same idea as
  keeping the Gemini calls in `llm_logic.py`: whoever is restyling the app and
  whoever is wiring up behaviour don't have to edit the same file. Nothing in
  here holds state or calls the LLM.
- `.streamlit/config.toml` — dark theme defaults so Streamlit's own widgets match
  the custom styling

## Already-included differentiator features

1. **Inbox Health Score** (sidebar) — aggregates urgency/frustration/open tasks
   across analyzed emails into one score. Click "Analyze all emails" to populate it.
2. **Reply confidence + human-review flag** — every draft reply comes with a
   confidence level (High/Medium/Low) and a reason, so the tool knows when
   NOT to auto-send (e.g. pricing, commitments, emotionally charged replies).
3. **Ask My Inbox** — natural-language questions across the whole inbox
   ("What are my upcoming deadlines?"), answered strictly from email context
   with the supporting emails cited as sources.
4. **Add to calendar** (sidebar, under Inbox Health) — after you analyze an
   email, this resolves its deadlines into real datetimes and exports them as
   a `.ics` file. The deadlines `analyze_email()` extracts are natural language
   ("tonight", "by Friday"), which no calendar can read, so `plan_calendar_events()`
   anchors them to the email's own timestamp: an email received Fri 18 Sep that
   says "Monday at 3 PM" becomes Mon 21 Sep 15:00. It refuses to invent dates —
   the newsletter email correctly yields zero events.

   The `.ics` imports into Apple Calendar, Outlook, or Google Calendar. Writing
   directly into someone's Google Calendar would need OAuth and a consent screen,
   which is why the export is a file rather than a live sync.

## Where to go next (suggested split)

- **Person 1 (LLM):** tune prompts in `llm_logic.py`, test edge cases (very short
  emails, multi-language, sarcasm), maybe add thread-context stitching using
  `thread_id` in emails.json
- **Person 2 (LLM/data):** expand `data/emails.json` with more variety, and/or
  build the thread-summary feature (combine e1 + e8, which share `thread_id`)
- **Person 3 (UI):** polish the look in `ui.py` — the colour ramp, the priority
  glyph, row density. `PRIORITY_COLOR` / `SENTIMENT_COLOR` / `CONFIDENCE_COLOR`
  are the single source of truth for what each colour means
- **Person 4 (UI):** add the deadline timeline view (new tab/section — collect
  all `Task.deadline` values across analyzed emails and show on a simple chart
  or sorted list)
- **Person 5 (data + demo):** stress-test the flow end-to-end, prepare the pitch,
  make sure the demo emails tell a clear "before/after" story

## Notes

- Analysis and drafts are cached in `st.session_state` so you don't burn API
  calls re-analyzing the same email on every rerun.
- If you hit Gemini free-tier rate limits during dev, stagger testing across
  teammates or add a short `time.sleep()` between calls in a loop.
- The `thread_id` field in emails.json lets you group e1 (initial outage report)
  and e8 (follow-up) — useful if you build thread-level context/summaries.
