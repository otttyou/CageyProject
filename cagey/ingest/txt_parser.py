"""Parse plain text chat exports using a regex cascade."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from dateutil import parser as date_parser

from cagey.ingest.base import BaseParser, Message, ParseError

# Patterns try most specific → least specific.
_PATTERNS = [
    # [2024-01-15 10:30:00] Alice: message
    re.compile(r"^\[(?P<ts>[^\]]+)\]\s*(?P<author>[^:]+):\s*(?P<content>.+)$"),
    # 2024-01-15 10:30:00 Alice: message
    re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{1,2}:\d{2}(?::\d{2})?)\s+(?P<author>[^:]+):\s*(?P<content>.+)$"
    ),
    # 10:30 Alice: message
    re.compile(r"^(?P<ts>\d{1,2}:\d{2}(?:\s?[APap][Mm])?)\s+(?P<author>[^:]+):\s*(?P<content>.+)$"),
    # Alice (10:30 AM): message
    re.compile(r"^(?P<author>[^()]+)\s*\((?P<ts>[^)]+)\):\s*(?P<content>.+)$"),
    # Alice: message (no timestamp)
    re.compile(r"^(?P<author>[A-Za-z][\w .'-]{0,40}):\s*(?P<content>.+)$"),
]


class TxtParser(BaseParser):
    """Heuristic parser for plain text chat exports."""

    def can_parse(self, path: Path) -> bool:
        return path.suffix.lower() in {".txt", ".log", ".md"}

    def parse(self, path: Path) -> list[Message]:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise ParseError(f"Could not read {path}: {exc}") from exc

        messages: list[Message] = []
        current: Message | None = None

        for idx, raw_line in enumerate(lines):
            line = raw_line.rstrip()
            if not line.strip():
                continue

            parsed = self._try_patterns(line, idx)
            if parsed is not None:
                if current is not None:
                    messages.append(current)
                current = parsed
            elif current is not None:
                # Continuation of the previous message.
                current.content = f"{current.content}\n{line}"

        if current is not None:
            messages.append(current)

        if not messages:
            raise ParseError(
                f"No messages could be parsed from {path}. "
                f"Expected lines like 'Alice: message' or '[timestamp] Alice: message'."
            )
        return messages

    @staticmethod
    def _try_patterns(line: str, index: int) -> Message | None:
        for pattern in _PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            groups = match.groupdict()
            author = groups["author"].strip()
            content = groups["content"].strip()
            if not author or not content:
                continue
            ts_raw = groups.get("ts")
            timestamp = _parse_timestamp(ts_raw, index)
            return Message(author=author, timestamp=timestamp, content=content)
        return None


def _parse_timestamp(raw: str | None, index: int) -> datetime:
    if not raw:
        return datetime.fromtimestamp(index, tz=timezone.utc)
    try:
        return date_parser.parse(raw)
    except (ValueError, TypeError):
        return datetime.fromtimestamp(index, tz=timezone.utc)
