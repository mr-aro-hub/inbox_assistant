from schemas import CalendarEvent, CalendarPlan, DraftReply, Email, EmailAnalysis, Task
from storage import InboxRepository


def email() -> Email:
    return Email(id="e-1", sender_name="Asha", sender_email="asha@example.com", subject="Plan", body="Please reply", timestamp="2026-09-19T10:00:00")


def test_repository_persists_normalized_email_analysis_and_tasks(tmp_path):
    repository = InboxRepository(tmp_path / "inbox.db")
    repository.seed_emails([email()])
    repository.seed_emails([email().model_copy(update={"subject": "Do not overwrite"})])
    assert repository.list_emails()[0].subject == "Plan"

    analysis = EmailAnalysis(summary="Reply this week.", priority="High", priority_reason="A response is requested.", sentiment="Neutral", suggested_tone="Friendly", tasks=[Task(description="Reply", deadline="Friday")])
    repository.save_analysis("e-1", analysis)
    assert repository.get_analysis("e-1") == analysis


def test_repository_persists_draft_and_replaces_calendar_plan(tmp_path):
    repository = InboxRepository(tmp_path / "inbox.db")
    repository.seed_emails([email()])
    draft = DraftReply(reply_text="Thanks", confidence="High", confidence_reason="Routine acknowledgement.", needs_human_review=False)
    repository.save_draft("e-1", draft)
    assert repository.get_draft("e-1") == draft

    first = CalendarPlan(events=[CalendarEvent(title="First", start="2026-09-20T09:00:00", end="2026-09-20T10:00:00", all_day=False, source="mail")])
    replacement = CalendarPlan(events=[CalendarEvent(title="Replacement", start="2026-09-21T09:00:00", end="2026-09-21T10:00:00", all_day=False, source="mail")])
    repository.save_calendar_plan("e-1", first)
    repository.save_calendar_plan("e-1", replacement)
    assert repository.get_calendar_plan("e-1") == replacement
