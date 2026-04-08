"""Parse JSON chat exports (Slack-like structure or generic list-of-objects)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dateutil import parser as date_parser

from cagey.ingest.base import BaseParser, Message, ParseError


class JsonParser(BaseParser):
    """Accepts JSON exports from Slack, Discord, or any tool that produces a list of messages."""

    def can_parse(self, path: Path) -> bool:
        if path.suffix.lower() != ".json":
            return False
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return False
        return isinstance(data, list)

    def parse(self, path: Path) -> list[Message]:
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ParseError(f"Invalid JSON in {path}: {exc}") from exc

        if not isinstance(data, list):
            raise ParseError(f"Expected JSON array at the top level of {path}.")

        messages: list[Message] = []
        for idx, raw in enumerate(data):
            if not isinstance(raw, dict):
                continue
            msg = self._parse_one(raw)
            if msg is not None:
                messages.append(msg)

            # Flatten Slack-style threaded replies.
            for reply in raw.get("replies", []) or []:
                if isinstance(reply, dict):
                    reply_msg = self._parse_one(reply, thread_id=raw.get("ts") or str(idx))
                    if reply_msg is not None:
                        messages.append(reply_msg)

        if not messages:
            raise ParseError(f"No messages could be extracted from {path}.")
        return messages

    def _parse_one(self, raw: dict[str, Any], thread_id: str | None = None) -> Message | None:
        author = (
            raw.get("user")
            or raw.get("author")
            or raw.get("name")
            or raw.get("from")
            or raw.get("username")
        )
        content = raw.get("text") or raw.get("message") or raw.get("content") or raw.get("body")
        ts_raw = raw.get("ts") or raw.get("timestamp") or raw.get("time") or raw.get("date")

        if not author or not content:
            return None

        timestamp = _parse_timestamp(ts_raw)
        channel = raw.get("channel") or raw.get("channel_name")

        return Message(
            author=str(author),
            timestamp=timestamp,
            content=str(content),
            channel=str(channel) if channel else None,
            thread_id=thread_id or (str(raw["thread_ts"]) if raw.get("thread_ts") else None),
        )


def _parse_timestamp(raw: Any) -> datetime:
    """Parse a timestamp from Slack float, epoch int, or ISO 8601 string."""
    if raw is None:
        return datetime.now(tz=timezone.utc)
    if isinstance(raw, (int, float)):
        return datetime.fromtimestamp(float(raw), tz=timezone.utc)
    if isinstance(raw, str):
        # Slack-style "1620000000.123456"
        try:
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        except ValueError:
            pass
        try:
            return date_parser.parse(raw)
        except (ValueError, TypeError):
            return datetime.now(tz=timezone.utc)
    return datetime.now(tz=timezone.utc)
