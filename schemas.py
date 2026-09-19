"""
Pydantic schemas for structured data throughout the app.
These define the exact shape of data we ask Gemini to return,
and the shape of our mock email records.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, List

# ---------- Input: mock email record ----------

class Email(BaseModel):
    id: str
    sender_name: str
    sender_email: str
    subject: str
    body: str
    timestamp: str  # ISO string, e.g. "2026-09-18T09:30:00"
    thread_id: Optional[str] = None  # emails sharing a thread_id are one conversation


# ---------- Output: what we ask Gemini to produce ----------

class Task(BaseModel):
    description: str
    deadline: Optional[str] = Field(
        default=None, description="Deadline in natural language or ISO date, if mentioned"
    )


class EmailAnalysis(BaseModel):
    summary: str = Field(description="2-3 sentence summary of the email/thread")
    priority: Literal["Urgent", "High", "Normal", "Low"]
    priority_reason: str = Field(description="One sentence explaining the priority level")
    tasks: list[Task] = Field(default_factory=list)
    sentiment: Literal["Positive", "Neutral", "Frustrated", "Urgent/Stressed"]
    suggested_tone: Literal["Formal", "Friendly", "Casual", "Apologetic"]


class DraftReply(BaseModel):
    reply_text: str
    confidence: Literal["High", "Medium", "Low"] = Field(
        description="How confident the model is this draft is safe to send with minimal edits"
    )
    confidence_reason: str = Field(
        description="Why this confidence level — e.g. involves a commitment, price, or date that needs human review"
    )
    needs_human_review: bool

class CalendarEvent(BaseModel):
    title: str = Field(description="Short, actionable calendar title")
    start: str = Field(description="Local start, ISO 8601, e.g. 2026-09-18T19:30:00")
    end: str = Field(description="Local end, ISO 8601, same format as start")
    all_day: bool = Field(
        description="True only when a date is known but no time of day"
    )
    source: str = Field(
        description="The task or phrase in the email this event was derived from"
    )


class CalendarPlan(BaseModel):
    events: list[CalendarEvent] = Field(default_factory=list)


class InboxSource(BaseModel):
    email_id: str
    subject: str
    sender: str


class InboxAnswer(BaseModel):
    answer: str
    sources: List[InboxSource]
