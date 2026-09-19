"""
AI Email Inbox Assistant — Streamlit app.
Run with: streamlit run main.py

Behaviour lives here; the stylesheet and HTML builders live in ui.py.
"""

import json
import streamlit as st

import ui
import calendar_export
from schemas import CalendarPlan, DraftReply, Email, EmailAnalysis
from storage import InboxRepository
from llm_logic import (
    analyze_email,
    draft_reply,
    answer_inbox_question,
    plan_calendar_events,
)

st.set_page_config(
    page_title="AI Inbox Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(ui.CSS, unsafe_allow_html=True)


# ---------- Data loading ----------

@st.cache_data
def load_emails():
    with open("data/emails.json") as f:
        raw = json.load(f)
    return [Email.model_validate(e) for e in raw]


repository = InboxRepository()
emails = repository.seed_emails(load_emails())

# session cache so we don't re-call the LLM every rerun
if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = {}
if "draft_cache" not in st.session_state:
    st.session_state.draft_cache = {}
if "calendar_cache" not in st.session_state:
    st.session_state.calendar_cache = {}

# Restore durable analysis results so the inbox health view survives an app restart.
for email in emails:
    if email.id not in st.session_state.analysis_cache:
        saved_analysis = repository.get_analysis(email.id)
        if saved_analysis:
            st.session_state.analysis_cache[email.id] = saved_analysis


def get_analysis(email: Email, refresh: bool = False):
    if email.id not in st.session_state.analysis_cache:
        if not refresh:
            saved_analysis = repository.get_analysis(email.id)
            if saved_analysis:
                st.session_state.analysis_cache[email.id] = saved_analysis
                return saved_analysis
        with st.spinner("Analyzing email..."):
            st.session_state.analysis_cache[email.id] = analyze_email(email)
            repository.save_analysis(email.id, st.session_state.analysis_cache[email.id])
    return st.session_state.analysis_cache[email.id]


def get_draft(email: Email, analysis, refresh: bool = False):
    if email.id not in st.session_state.draft_cache:
        if not refresh:
            saved_draft = repository.get_draft(email.id)
            if saved_draft:
                st.session_state.draft_cache[email.id] = saved_draft
                return saved_draft
        with st.spinner("Drafting reply..."):
            st.session_state.draft_cache[email.id] = draft_reply(email, analysis)
            repository.save_draft(email.id, st.session_state.draft_cache[email.id])
    return st.session_state.draft_cache[email.id]


def get_calendar(email: Email, analysis, refresh: bool = False):
    if email.id not in st.session_state.calendar_cache:
        if not refresh:
            saved_plan = repository.get_calendar_plan(email.id)
            if saved_plan:
                st.session_state.calendar_cache[email.id] = saved_plan
                return saved_plan
        with st.spinner("Finding dates..."):
            st.session_state.calendar_cache[email.id] = plan_calendar_events(
                email, analysis
            )
            repository.save_calendar_plan(email.id, st.session_state.calendar_cache[email.id])
    return st.session_state.calendar_cache[email.id]


def html(fragment: str):
    st.markdown(fragment, unsafe_allow_html=True)


# ---------- Sidebar: Inbox Health Score ----------

with st.sidebar:
    html(ui.workspace_header("Inbox Assistant"))

    if st.button("Analyze all emails", key="analyze_all"):
        for e in emails:
            get_analysis(e)

    analyzed = [
        st.session_state.analysis_cache[e.id]
        for e in emails
        if e.id in st.session_state.analysis_cache
    ]

    html(ui.section_label("Inbox health"))

    if analyzed:
        urgent_count = sum(1 for a in analyzed if a.priority == "Urgent")
        high_count = sum(1 for a in analyzed if a.priority == "High")
        total_tasks = sum(len(a.tasks) for a in analyzed)
        frustrated_count = sum(
            1 for a in analyzed if a.sentiment in ("Frustrated", "Urgent/Stressed")
        )

        # simple health score: starts at 100, deducted for each stressor
        score = 100 - (urgent_count * 20) - (high_count * 10) - (frustrated_count * 10)
        score = max(score, 0)

        html(ui.health_score(score))
        html(ui.health_stat("Urgent", urgent_count, ui.RED))
        html(ui.health_stat("High priority", high_count, ui.ORANGE))
        html(ui.health_stat("Frustrated senders", frustrated_count, ui.ORANGE))
        html(ui.health_stat("Open tasks", total_tasks, ui.GREY))
    else:
        html(
            '<div class="side-note">Click &ldquo;Analyze all emails&rdquo; '
            "to see your inbox health score.</div>"
        )

# the Calendar section and the footer are written to the sidebar further down,
# once the detail pane has resolved which email is selected and analyzed


# ---------- Ask My Inbox ----------

html(
    '<div class="topbar">'
    '<span class="topbar-title">Ask my inbox</span>'
    '<span class="topbar-hint">Answered only from the emails below</span>'
    "</div>"
)

ask_col, btn_col = st.columns([7, 1], vertical_alignment="bottom")

with ask_col:
    question = st.text_input(
        "What would you like to know?",
        placeholder="e.g. What are my upcoming deadlines?",
    )

with btn_col:
    asked = st.button("Ask", key="ask_inbox_btn", type="primary")

if asked:
    if not question.strip():
        html(ui.callout("Please enter a question.", "warn"))
    else:
        with st.spinner("Searching your inbox..."):
            result = answer_inbox_question(question, emails)

        html('<div class="answer-wrap">')
        html(ui.section_label("Answer"))
        html(f'<div class="answer">{result.answer}</div>')

        if result.sources:
            html(ui.section_label("Sources"))
            for source in result.sources:
                html(ui.source_row(source.subject, source.sender, source.email_id))
        else:
            html('<div class="empty">No supporting emails found.</div>')

        html("</div>")

html('<div class="rule"></div>')


# ---------- Inbox + detail ----------

col_list, col_detail = st.columns([1, 1.9], gap="large")

with col_list:
    selected_id = st.session_state.get("selected_id", emails[0].id)

    # group rows by priority, the way the analysis actually labelled them
    priorities = {}
    for e in emails:
        cached = st.session_state.analysis_cache.get(e.id)
        priorities[e.id] = cached.priority if cached else "Unanalyzed"

    html(ui.row_rules(priorities, selected_id))

    html(
        '<div class="topbar" style="padding-bottom:2px">'
        '<span class="topbar-title">Inbox</span>'
        f'<span class="topbar-count">{len(emails)}</span>'
        "</div>"
    )

    for group in ("Urgent", "High", "Normal", "Low", "Unanalyzed"):
        in_group = [e for e in emails if priorities[e.id] == group]
        if not in_group:
            continue

        html(ui.group_header(group, len(in_group)))

        for e in in_group:
            label = (
                f"`{e.id.upper()}` {e.subject}\n\n"
                f"{e.sender_name} · {e.timestamp[:10]}"
            )
            if st.button(label, key=f"select_{e.id}"):
                st.session_state.selected_id = e.id
                selected_id = e.id

selected_email = next(e for e in emails if e.id == selected_id)

with col_detail:
    html(
        ui.detail_header(
            selected_email.subject,
            selected_email.sender_name,
            selected_email.sender_email,
            selected_email.timestamp,
        )
    )
    html(ui.mail_body(selected_email.body))
    html('<div class="rule"></div>')

    if st.button("Analyze this email", key="analyze_btn"):
        st.session_state.analysis_cache.pop(selected_email.id, None)  # force refresh
        get_analysis(selected_email, refresh=True)
        # the inbox list renders before this column, so it would otherwise keep
        # showing the email under "Unanalyzed" until the next click. The result
        # is cached, so this rerun costs no API call.
        st.rerun()

    analysis = st.session_state.analysis_cache.get(selected_email.id)

    if analysis:
        html(ui.section_label("Analysis"))
        html(
            ui.stat_row(
                [
                    ("Priority", analysis.priority, ui.PRIORITY_COLOR[analysis.priority]),
                    ("Sentiment", analysis.sentiment, ui.SENTIMENT_COLOR[analysis.sentiment]),
                    ("Suggested tone", analysis.suggested_tone, ui.GREY),
                ]
            )
        )
        html(ui.summary_block(analysis.summary, f"Why this priority: {analysis.priority_reason}"))

        html(ui.section_label("Extracted tasks"))
        if analysis.tasks:
            html(ui.task_list([(t.description, t.deadline) for t in analysis.tasks]))
        else:
            html('<div class="empty">No action items detected.</div>')

        html('<div class="rule"></div>')

        if st.button("Draft a reply", key="draft_btn"):
            st.session_state.draft_cache.pop(selected_email.id, None)
            get_draft(selected_email, analysis, refresh=True)

        draft = st.session_state.draft_cache.get(selected_email.id)
        if draft:
            html(ui.section_label("Suggested reply"))
            st.text_area(
                "Draft",
                draft.reply_text,
                height=190,
                key=f"draft_text_{selected_email.id}",
            )

            html(ui.confidence_line(draft.confidence, draft.confidence_reason))

            if draft.needs_human_review:
                html(ui.callout("This draft needs your review before sending.", "warn"))
            else:
                html(ui.callout("Safe to send with minimal edits.", "ok"))
    else:
        html(
            '<div class="empty">Click &ldquo;Analyze this email&rdquo; to generate '
            "a summary, priority, tasks, and sentiment.</div>"
        )


# ---------- Sidebar: Add to calendar ----------
# Written here rather than in the sidebar block above so it reflects the email
# you just analyzed, instead of trailing a rerun behind it.

with st.sidebar:
    html(ui.section_label("Calendar"))

    if not analysis:
        html(
            '<div class="side-note">Analyze an email to pull its dates '
            "out into calendar events.</div>"
        )
    else:
        html(f'<div class="cal-context">{selected_email.subject}</div>')

        if st.button("Add to calendar", key="calendar_btn"):
            st.session_state.calendar_cache.pop(selected_email.id, None)
            get_calendar(selected_email, analysis, refresh=True)

        plan = st.session_state.calendar_cache.get(selected_email.id)

        if plan:
            usable = calendar_export.usable_events(plan.events)

            if usable:
                for event, start, end in usable:
                    html(
                        ui.calendar_item(
                            event.title,
                            ui.when_label(start, end, event.all_day),
                            event.source,
                        )
                    )

                st.download_button(
                    f"Download .ics ({len(usable)})",
                    data=calendar_export.build_ics(usable, selected_email.subject),
                    file_name=f"{selected_email.id}-calendar.ics",
                    mime="text/calendar",
                    key="ics_dl",
                )
            else:
                html(
                    '<div class="side-note">Nothing in this email has a date '
                    "concrete enough to schedule.</div>"
                )

    html(
        f'<div class="side-foot">{len(emails)} emails in inbox '
        f"&middot; analyzed {len(analyzed)}</div>"
    )
