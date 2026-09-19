"""
AI Email Inbox Assistant — Streamlit app.
Run with: streamlit run main.py

Behaviour lives here; the stylesheet and HTML builders live in ui.py.
"""

import json
import streamlit as st
from datetime import date
import ui
def html(content):
    st.markdown(content, unsafe_allow_html=True)

import calendar_export
from schemas import Email
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


emails = load_emails()

# session cache so we don't re-call the LLM every rerun
if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = {}
if "draft_cache" not in st.session_state:
    st.session_state.draft_cache = {}
if "calendar_cache" not in st.session_state:
    st.session_state.calendar_cache = {}


def get_analysis(email: Email):
    if email.id not in st.session_state.analysis_cache:
        with st.spinner("Analyzing email..."):
            st.session_state.analysis_cache[email.id] = analyze_email(email)
    return st.session_state.analysis_cache[email.id]


def get_draft(email: Email, analysis):
    if email.id not in st.session_state.draft_cache:
        with st.spinner("Drafting reply..."):
            st.session_state.draft_cache[email.id] = draft_reply(email, analysis)
    return st.session_state.draft_cache[email.id]


def get_calendar(email: Email, analysis):
    if email.id not in st.session_state.calendar_cache:
        with st.spinner("Finding dates..."):
            st.session_state.calendar_cache[email.id] = plan_calendar_events(
                email, analysis
            )
    return st.session_state.calendar_cache[email.id]

def get_all_calendar_events():
    """Collect calendar events from all analyzed emails."""

    rows = []

    priority_rank = {
        "Urgent": 4,
        "High": 3,
        "Normal": 2,
        "Low": 1,
    }

    for email_id, plan in st.session_state.calendar_cache.items():

        email = next(
            (e for e in emails if e.id == email_id),
            None
        )

        if not email:
            continue

        analysis = st.session_state.analysis_cache.get(email_id)

        priority = (
            analysis.priority
            if analysis
            else "Normal"
        )

        for event, start, end in calendar_export.usable_events(
            plan.events
        ):
            rows.append({
                "email_id": email_id,
                "email_subject": email.subject,
                "sender": email.sender_name,
                "event": event,
                "start": start,
                "end": end,
                "priority": priority,
            })

    return sorted(
        rows,
        key=lambda x: (
            x["start"],
            -priority_rank.get(x["priority"], 0),
        )
    )


# ---------- Sidebar: Inbox Health Score ----------

with st.sidebar:
    html(ui.workspace_header("Inbox Assistant"))

    if st.button("Analyze all emails", key="analyze_all"):

        progress = st.progress(0)

        for i, e in enumerate(emails):

            try:
                # 1. Analyze the email
                analysis = get_analysis(e)

                # 2. Automatically extract calendar events
                get_calendar(e, analysis)

                # 3. Update progress
                progress.progress((i + 1) / len(emails))

            except Exception as ex:

                if "429" in str(ex) or "RESOURCE_EXHAUSTED" in str(ex):

                    st.warning(
                        f"Gemini rate limit reached after {i} emails. "
                        "Wait about 1 minute and click 'Analyze all emails' again."
                    )

                    break

                raise

        progress.empty()

        st.rerun()

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

        st.session_state.analysis_cache.pop(
            selected_email.id,
            None
        )

        st.session_state.calendar_cache.pop(
            selected_email.id,
            None
        )

        analysis = get_analysis(selected_email)

        get_calendar(
            selected_email,
            analysis
        )

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
            get_draft(selected_email, analysis)

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


# ---------- Sidebar: Calendar ----------

with st.sidebar:

    html(ui.section_label("Calendar"))

    calendar_events = get_all_calendar_events()

    today = date.today()

    # Month calendar
    html(
        ui.mini_calendar(
            today.year,
            today.month,
            calendar_events,
        )
    )

    # Event list
    month_events = [
        item
        for item in calendar_events
        if item["start"].year == today.year
        and item["start"].month == today.month
    ]

    if month_events:

        html(
            '<div class="section" style="padding-top:4px">'
            'Upcoming'
            '</div>'
        )

        for item in month_events[:4]:

            html(
                ui.calendar_item(
                    item["event"].title,
                    ui.when_label(
                        item["start"],
                        item["end"],
                        item["event"].all_day,
                    ),
                    item["sender"],
                    item["priority"],
                )
            )

    else:

        html(
            '<div class="side-note">'
            'No calendar events yet.'
            '</div>'
        )

