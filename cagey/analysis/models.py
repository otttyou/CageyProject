"""Pydantic models for Cagey analysis results."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from cagey.ingest.base import Message


class SubAuditionCategory(str, Enum):
    """Taxonomy of implicit communicative acts that Cagey detects."""

    POWER_PLAY = "power_play"
    PASSIVE_AGGRESSION = "passive_aggression"
    DEFLECTION = "deflection"
    ALLIANCE_SEEKING = "alliance_seeking"
    URGENCY_SIGNALING = "urgency_signaling"
    APPROVAL_SEEKING = "approval_seeking"
    THREAT_IMPLICIT = "threat_implicit"
    SARCASM = "sarcasm"
    DISMISSAL = "dismissal"
    NONE = "none"

    @property
    def display_name(self) -> str:
        return self.value.replace("_", " ").title()


class SubAudition(BaseModel):
    """A single sub-audition detected in a message."""

    category: SubAuditionCategory
    confidence: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    quoted_trigger: str


class SentimentScore(BaseModel):
    """Sentiment classification for a single message."""

    label: Literal["positive", "negative", "neutral", "mixed"]
    score: float = Field(..., ge=-1.0, le=1.0)
    emotional_tone: str


class SerializedMessage(BaseModel):
    """A Message serialized for JSON storage."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    author: str
    timestamp: datetime
    content: str
    channel: str | None = None
    thread_id: str | None = None

    @classmethod
    def from_message(cls, msg: Message) -> "SerializedMessage":
        return cls(
            id=msg.id,
            author=msg.author,
            timestamp=msg.timestamp,
            content=msg.content,
            channel=msg.channel,
            thread_id=msg.thread_id,
        )

    def to_message(self) -> Message:
        return Message(
            id=self.id,
            author=self.author,
            timestamp=self.timestamp,
            content=self.content,
            channel=self.channel,
            thread_id=self.thread_id,
        )


class AnalysisResult(BaseModel):
    """The full analysis output for one message."""

    message: SerializedMessage
    sentiment: SentimentScore
    sub_auditions: list[SubAudition]
    summary: str
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    model_used: str = ""
    tokens_used: int = 0
    error: str | None = None

    @property
    def primary_sub_audition(self) -> SubAudition | None:
        """Return the highest-confidence sub-audition, or None if no meaningful ones exist."""
        meaningful = [sa for sa in self.sub_auditions if sa.category != SubAuditionCategory.NONE]
        if not meaningful:
            return None
        return max(meaningful, key=lambda sa: sa.confidence)
