"""Privacy controls applied before email content is sent to an LLM provider."""

from __future__ import annotations

import re

from schemas import Email


EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_RE = re.compile(r"(?x)(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)")


def redact_text(value: str) -> str:
    """Replace direct contact identifiers while retaining the business context."""
    value = EMAIL_RE.sub("[redacted-email]", value)
    return PHONE_RE.sub("[redacted-phone]", value)


def redact_email(email: Email) -> Email:
    """Return a copy that is safe to provide to the configured model provider."""
    return email.model_copy(
        update={
            "sender_email": "[redacted-email]",
            "body": redact_text(email.body),
        }
    )
