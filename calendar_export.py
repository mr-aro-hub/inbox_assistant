"""
Turns planned calendar events into a downloadable .ics file.

No calendar account or API is involved: an .ics is the interchange format
every calendar app reads, so the file opens straight into Apple Calendar,
Outlook, or Google Calendar's import. Stdlib only.

RFC 5545 is picky about two things that silently break imports — CRLF line
endings and folding long lines — so both are handled here rather than by
string-joining the file inline.
"""

from datetime import datetime, timezone
from uuid import uuid4

from schemas import CalendarEvent

MAX_OCTETS = 73  # RFC 5545 says 75; leaving slack for the folding space


def _parse(value: str) -> datetime | None:
    """Accept what the model returned, or give up on this event."""
    try:
        parsed = datetime.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None
    # the prompt asks for local times; drop any offset rather than convert
    return parsed.replace(tzinfo=None)


def usable_events(
    events: list[CalendarEvent],
) -> list[tuple[CalendarEvent, datetime, datetime]]:
    """
    Keep only events with datetimes we can actually parse, so the sidebar
    lists exactly what the .ics will contain — no silent drops at download.
    """
    usable = []

    for event in events:
        start = _parse(event.start)
        end = _parse(event.end)

        if start is None:
            continue
        if end is None or end <= start:
            end = start  # a zero-length marker still imports fine

        usable.append((event, start, end))

    return sorted(usable, key=lambda row: row[1])


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Split to <=75 octets per line, continuations prefixed with a space."""
    raw = line.encode("utf-8")
    if len(raw) <= MAX_OCTETS:
        return line

    chunks = []
    while len(raw) > MAX_OCTETS:
        cut = MAX_OCTETS
        # never split in the middle of a UTF-8 sequence
        while cut > 0 and (raw[cut] & 0xC0) == 0x80:
            cut -= 1
        chunks.append(raw[:cut])
        raw = raw[cut:]
    chunks.append(raw)

    return "\r\n ".join(chunk.decode("utf-8") for chunk in chunks)


def build_ics(
    usable: list[tuple[CalendarEvent, datetime, datetime]],
    email_subject: str,
) -> str:
    """Serialize the events returned by usable_events() into one calendar."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AI Inbox Assistant//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for event, start, end in usable:
        if event.all_day:
            dtstart = f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}"
            dtend = f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}"
        else:
            dtstart = f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}"
            dtend = f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}"

        description = f"From email: {email_subject}"
        if event.source:
            description += f"\n\n{event.source}"

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid4()}@inbox-assistant",
            f"DTSTAMP:{stamp}",
            dtstart,
            dtend,
            f"SUMMARY:{_escape(event.title)}",
            f"DESCRIPTION:{_escape(description)}",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")

    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
