"""Base types shared by all chat parsers."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


class ParseError(Exception):
    """Raised when a chat file cannot be parsed."""


@dataclass
class Message:
    """A single normalized chat message."""

    author: str
    timestamp: datetime
    content: str
    channel: str | None = None
    thread_id: str | None = None
    id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.id:
            payload = f"{self.author}|{self.timestamp.isoformat()}|{self.content}"
            self.id = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


class BaseParser(ABC):
    """Abstract base class for chat parsers."""

    @abstractmethod
    def can_parse(self, path: Path) -> bool:
        """Return True if this parser can handle the given file."""

    @abstractmethod
    def parse(self, path: Path) -> list[Message]:
        """Parse the file into a list of Messages."""
