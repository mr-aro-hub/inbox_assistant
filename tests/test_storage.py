from schemas import Email, EmailAnalysis
from storage import InboxRepository


def test_repository_seeds_once_and_persists_an_analysis(tmp_path):
    repo = InboxRepository(tmp_path / "inbox.db")
    email = Email(id="e1", sender_name="A", sender_email="a@example.com", subject="S", body="B", timestamp="2026-09-19T10:00:00")
    assert repo.seed_emails([email]) == [email]
    repo.seed_emails([email.model_copy(update={"subject": "Changed"})])
    assert repo.list_emails()[0].subject == "S"

    analysis = EmailAnalysis(summary="Needs an answer.", priority="High", priority_reason="Deadline this week.", sentiment="Neutral", suggested_tone="Friendly")
    repo.save("e1", "analysis", analysis)
    assert repo.load("e1", "analysis", EmailAnalysis) == analysis
    repo.clear("e1", "analysis")
    assert repo.load("e1", "analysis", EmailAnalysis) is None
