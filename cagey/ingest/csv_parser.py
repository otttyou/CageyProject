"""Parse CSV chat exports with column auto-detection."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from dateutil import parser as date_parser

from cagey.ingest.base import BaseParser, Message, ParseError

_AUTHOR_KEYS = ("author", "user", "name", "from", "username", "sender", "speaker")
_CONTENT_KEYS = ("text", "message", "content", "body", "msg")
_TIMESTAMP_KEYS = ("timestamp", "ts", "date", "time", "datetime", "sent_at", "created_at")
_CHANNEL_KEYS = ("channel", "channel_name", "room", "conversation")


class CsvParser(BaseParser):
    """Accepts CSV files with common column names for author, message, and timestamp."""

    def can_parse(self, path: Path) -> bool:
        return path.suffix.lower() == ".csv"

    def parse(self, path: Path) -> list[Message]:
        try:
            with path.open("r", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                if reader.fieldnames is None:
                    raise ParseError(f"CSV file {path} has no header row.")

                column_map = self._map_columns(reader.fieldnames)
                missing = [k for k in ("author", "content") if k not in column_map]
                if missing:
                    raise ParseError(
                        f"CSV {path} is missing required columns: {missing}. "
                        f"Found columns: {reader.fieldnames}"
                    )

                messages: list[Message] = []
                for idx, row in enumerate(reader):
                    author = (row.get(column_map["author"]) or "").strip()
                    content = (row.get(column_map["content"]) or "").strip()
                    if not author or not content:
                        continue

                    ts_raw = (
                        row.get(column_map["timestamp"])
                        if "timestamp" in column_map
                        else None
                    )
                    timestamp = _parse_timestamp(ts_raw, fallback_index=idx)
                    channel = (
                        row.get(column_map["channel"]) if "channel" in column_map else None
                    )

                    messages.append(
                        Message(
                            author=author,
                            timestamp=timestamp,
                            content=content,
                            channel=channel.strip() if channel else None,
                        )
                    )
        except OSError as exc:
            raise ParseError(f"Could not read {path}: {exc}") from exc

        if not messages:
            raise ParseError(f"No valid rows found in CSV {path}.")
        return messages

    @staticmethod
    def _map_columns(fieldnames: list[str] | None) -> dict[str, str]:
        column_map: dict[str, str] = {}
        if not fieldnames:
            return column_map
        lower = {f.lower().strip(): f for f in fieldnames}

        for key in _AUTHOR_KEYS:
            if key in lower:
                column_map["author"] = lower[key]
                break
        for key in _CONTENT_KEYS:
            if key in lower:
                column_map["content"] = lower[key]
                break
        for key in _TIMESTAMP_KEYS:
            if key in lower:
                column_map["timestamp"] = lower[key]
                break
        for key in _CHANNEL_KEYS:
            if key in lower:
                column_map["channel"] = lower[key]
                break
        return column_map


def _parse_timestamp(raw: str | None, fallback_index: int) -> datetime:
    if not raw:
        # Synthesize monotonically increasing timestamps for undated rows.
        return datetime.fromtimestamp(fallback_index, tz=timezone.utc)
    try:
        return date_parser.parse(raw)
    except (ValueError, TypeError):
        return datetime.fromtimestamp(fallback_index, tz=timezone.utc)
