Inbox Assistant
Most of my inbox doesn't need me. The problem is that it all looks the same until I've read it.
This is  attempt at fixing that. It's a Streamlit app that reads an inbox, works out what's actually urgent and why, drafts replies it's willing to stand behind, answers questions about what's sitting in there, and pulls real deadlines out into our calendar.

Built on Google Gemini with Pydantic schemas, so every model response comes back as validated structured data rather than a blob of prose I'd have to parse.

## Run locally

From the project folder, create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies, then create a `.env` file from the supplied template and add
your Gemini API key:

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
```

Your `.env` file must contain:

```text
GEMINI_API_KEY=your_gemini_api_key_here
```

Start Streamlit:

```powershell
streamlit run main.py
```

Open the URL shown in the terminal (normally `http://localhost:8501`). On first run,
the app creates `data/inbox.db` automatically and seeds it from `data/emails.json`.
The database is local-only and is ignored by Git.

What it does
Tells me what's urgent, and why
Every email gets a summary, a priority, the action items with their deadlines, the sender's emotional state, and the tone a reply should take.

The priority_reason field is the part I care about. A priority label on its own is just the model asserting something — "Urgent" tells me nothing I can check. Making it explain itself ("the outage threatens a client demo scheduled for tomorrow morning") means I can disagree with it in about a second, which is the whole point.

Drafts replies it knows when not to send
Every draft comes back with a confidence level and a reason, and anything below High gets flagged for review.

This mattered more than I expected. An assistant that writes a confident reply committing to a delivery date it invented is worse than no assistant at all. So the model has to classify its own output: routine acknowledgement, or something touching pricing, commitments, or an angry customer. Those last ones are always gated. The frustrated-client email in the sample data reliably comes back Low — needs review, which is exactly right.

Answers questions about the whole inbox
Ask "what are my upcoming deadlines?" or "which clients are unhappy?" and it answers from the emails and nothing else.

It's grounded on purpose. The prompt forbids outside knowledge, forbids inventing dates and names, and requires it to return the specific emails its answer came from — they render underneath as sources. If the answer isn't in the inbox it says so instead of guessing. An assistant that confidently makes up a deadline is a liability.

Scores the inbox
One number in the sidebar, deducted from 100 for each stressor: urgent emails, high-priority ones, and senders who are visibly annoyed. Deliberately crude — it's a glanceable "how bad is it" signal, not an analytic.

Puts deadlines in my calendar
This is the piece I'm most pleased with, because the obvious version doesn't work.

The analysis extracts deadlines the way humans write them: "tonight", "by 8 PM today", "end of day", "Monday at 3 PM". None of that is a date. You can't hand "tonight" to a calendar.

So there's a second pass that resolves those against the email's own timestamp. An email that arrived Friday 18 September saying "still on for Monday at 3 PM?" becomes Monday 21 September, 15:00–16:00 — an actual Monday, because the resolution is anchored to when the email landed rather than to today. Deadlines become a 30-minute block ending when the thing is due, so it shows up as time I need to protect rather than a zero-length marker I'll scroll past.

It's also told, firmly, not to invent dates. The newsletter in the sample data produces zero events, which is the correct answer and the one an over-eager model gets wrong.

The result exports as a .ics — the interchange format every calendar app reads, so it imports into Apple Calendar, Outlook or Google without any account setup. Writing directly into a Google Calendar would mean OAuth and a consent screen, which is a real project rather than a feature. A file was the honest scope.

Running it
python -m venv .venv
source .venv/bin/activate     # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # Windows PowerShell: copy .env.example .env
Put a Gemini API key in .env (free from aistudio.google.com), then:

streamlit run main.py
It opens on http://localhost:8501.

Build your own venv, don't copy someone else's. A virtualenv hardcodes the path of the Python that created it into pyvenv.cfg, so a committed one breaks for everybody else. If you ever see did not find executable at '...python.exe', that's what happened — delete the directory and rebuild.

.env is gitignored, and it should stay that way. A key committed once is a key in the history forever, and deleting it later doesn't help.

How it's put together
main.py              app flow and layout
ui.py                stylesheet and the HTML builders main.py renders
llm_logic.py         every Gemini call
calendar_export.py   .ics serialisation, stdlib only
schemas.py           Pydantic models — the contract for model output
data/emails.json     8 sample emails
The split is deliberate. llm_logic.py holds all four model calls and nothing else, so prompts can be tuned without touching the app. ui.py holds the styling for the same reason in reverse — restyling shouldn't mean editing application logic. And calendar_export.py is pure functions with no LLM and no state, which is why the .ics output is the one part of this I could test properly.

schemas.py is doing more work than its size suggests. The Pydantic models are passed to Gemini as the response schema, so the structure is enforced on the way out rather than validated hopefully on the way in. When the model returns a priority, it's one of four values or the request fails — there's no string-matching against "urgent" vs "Urgent" anywhere in the UI.

On the interface
Dense, quiet, keyboard-adjacent — modelled on issue trackers like Linear rather than on webmail. Rows group by priority under their own headers, a three-bar glyph carries the priority, and colour means one thing consistently: red is urgent, amber wants attention, green is fine. That ramp is defined once in ui.py and reused by priority, sentiment and draft confidence, so nothing has to be re-learned per panel.

Mostly it's about what isn't there. No cards, no borders, no drop shadows — just hairline rules and a hover state. Chrome competes with content, and the content here is eight emails that need triaging.

Known limits
The sample inbox is 8 mock emails in a JSON file. No Gmail connection yet.
Analysis and drafts are cached per session, so a rerun doesn't re-bill the API, but nothing persists once the app stops.
The Ask My Inbox answer clears when you select a different email — it isn't held in session state yet.
Every analysis is one API call. On the Gemini free tier, "Analyze all emails" is eight of them back to back, which can hit a rate limit.
Next
Gmail integration, so it reads a real inbox
Thread-level context — the sample data has thread_id on two emails that are the same conversation, and analysing them together would read much better than analysing them apart
Follow-up tracking: I promised Priya a status update by 8pm and never sent it
Embeddings for retrieval, once the inbox is bigger than fits in one promptort)
  and e8 (follow-up) — useful if you build thread-level context/summaries.
