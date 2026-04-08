"""Chat ingestion: parse various chat export formats into normalized Messages."""

from pathlib import Path

from cagey.ingest.base import BaseParser, Message, ParseError
from cagey.ingest.csv_parser import CsvParser
from cagey.ingest.json_parser import JsonParser
from cagey.ingest.txt_parser import TxtParser

__all__ = [
    "BaseParser",
    "Message",
    "ParseError",
    "load_messages",
    "PARSERS",
]

PARSERS: list[BaseParser] = [JsonParser(), CsvParser(), TxtParser()]


def load_messages(path: Path, format: str = "auto") -> list[Message]:
    """Parse a chat file into a list of Messages.

    Args:
        path: Path to the chat file.
        format: One of "auto", "json", "csv", "txt".
    """
    if not path.exists():
        raise FileNotFoundError(f"Chat file not found: {path}")

    if format == "auto":
        for parser in PARSERS:
            if parser.can_parse(path):
                return parser.parse(path)
        raise ParseError(
            f"Could not auto-detect format for {path}. "
            f"Specify --format explicitly (json, csv, or txt)."
        )

    name_map = {"json": JsonParser(), "csv": CsvParser(), "txt": TxtParser()}
    parser = name_map.get(format)
    if parser is None:
        raise ValueError(f"Unknown format: {format!r}. Use one of: json, csv, txt, auto.")
    return parser.parse(path)
