from datetime import datetime

from calendar_export import build_ics, usable_events
from schemas import CalendarEvent


def test_calendar_export_uses_crlf_escapes_text_and_discards_invalid_dates():
    valid = CalendarEvent(
        title="Call, A; B", start="2026-09-21T15:00:00", end="2026-09-21T16:00:00",
        all_day=False, source="Discuss integration\nwith the team",
    )
    invalid = CalendarEvent(title="Bad", start="not-a-date", end="also-bad", all_day=False, source="")
    usable = usable_events([invalid, valid])
    assert [(event.title, start) for event, start, _ in usable] == [("Call, A; B", datetime(2026, 9, 21, 15))]
    output = build_ics(usable, "Roadmap, Q4")
    assert "\r\n" in output and "\n" not in output.replace("\r\n", "")
    unfolded = output.replace("\r\n ", "")
    assert "SUMMARY:Call\\, A\\; B" in unfolded
    assert "DESCRIPTION:From email: Roadmap\\, Q4\\n\\nDiscuss integration\\nwith the team" in unfolded
