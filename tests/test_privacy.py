from privacy import redact_email, redact_text
from schemas import Email


def test_redact_text_removes_contact_identifiers():
    value = "Email alex@example.com or call +1 (415) 555-0123."
    assert redact_text(value) == "Email [redacted-email] or call [redacted-phone]."


def test_redact_email_keeps_email_context_but_not_sender_address():
    email = Email(
        id="x", sender_name="Alex", sender_email="alex@example.com", subject="Hello",
        body="Contact me at alex@example.com", timestamp="2026-09-19T10:00:00",
    )
    safe = redact_email(email)
    assert safe.subject == "Hello"
    assert safe.sender_email == "[redacted-email]"
    assert "alex@example.com" not in safe.body
