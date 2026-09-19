import llm_logic
from schemas import Email, InboxAnswer, InboxSource


def test_inbox_question_is_redacted_and_unknown_citations_are_removed(monkeypatch):
    captured = {}

    def fake_generate(prompt, schema):
        captured["prompt"] = prompt
        return InboxAnswer(
            answer="Found it.",
            sources=[
                InboxSource(email_id="known", subject="Real", sender="A"),
                InboxSource(email_id="invented", subject="Fake", sender="B"),
            ],
        )

    monkeypatch.setattr(llm_logic, "_generate", fake_generate)
    email = Email(id="known", sender_name="A", sender_email="a@example.com", subject="Hello", body="Call 415-555-0123", timestamp="2026-09-19T10:00:00")
    answer = llm_logic.answer_inbox_question("Email me at user@example.com", [email])
    assert "a@example.com" not in captured["prompt"]
    assert "user@example.com" not in captured["prompt"]
    assert "415-555-0123" not in captured["prompt"]
    assert [source.email_id for source in answer.sources] == ["known"]
