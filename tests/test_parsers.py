"""Tests for the three chat parsers."""

from pathlib import Path

import pytest

from cagey.ingest import load_messages
from cagey.ingest.base import Message, ParseError
from cagey.ingest.csv_parser import CsvParser
from cagey.ingest.json_parser import JsonParser
from cagey.ingest.txt_parser import TxtParser

FIXTURES = Path(__file__).parent / "fixtures"


class TestJsonParser:
    def test_can_parse_json(self):
        assert JsonParser().can_parse(FIXTURES / "sample.json")

    def test_cannot_parse_csv(self):
        assert not JsonParser().can_parse(FIXTURES / "sample.csv")

    def test_parses_messages(self):
        msgs = JsonParser().parse(FIXTURES / "sample.json")
        assert len(msgs) == 8
        authors = {m.author for m in msgs}
        assert "Alice" in authors and "Bob" in authors

    def test_all_messages_have_content(self):
        msgs = JsonParser().parse(FIXTURES / "sample.json")
        for m in msgs:
            assert m.content.strip()
            assert m.author.strip()

    def test_channel_preserved(self):
        msgs = JsonParser().parse(FIXTURES / "sample.json")
        assert all(m.channel == "general" for m in msgs)

    def test_message_id_set(self):
        msgs = JsonParser().parse(FIXTURES / "sample.json")
        ids = [m.id for m in msgs]
        assert len(set(ids)) == len(ids), "All message IDs should be unique"


class TestCsvParser:
    def test_can_parse_csv(self):
        assert CsvParser().can_parse(FIXTURES / "sample.csv")

    def test_cannot_parse_txt(self):
        assert not CsvParser().can_parse(FIXTURES / "sample.txt")

    def test_parses_messages(self):
        msgs = CsvParser().parse(FIXTURES / "sample.csv")
        assert len(msgs) == 5

    def test_author_column_detected(self):
        msgs = CsvParser().parse(FIXTURES / "sample.csv")
        assert msgs[0].author == "Alice"

    def test_timestamps_parsed(self):
        msgs = CsvParser().parse(FIXTURES / "sample.csv")
        assert msgs[0].timestamp.year == 2024


class TestTxtParser:
    def test_can_parse_txt(self):
        assert TxtParser().can_parse(FIXTURES / "sample.txt")

    def test_parses_messages(self):
        msgs = TxtParser().parse(FIXTURES / "sample.txt")
        assert len(msgs) == 5

    def test_author_extracted(self):
        msgs = TxtParser().parse(FIXTURES / "sample.txt")
        assert msgs[0].author == "Alice"

    def test_content_extracted(self):
        msgs = TxtParser().parse(FIXTURES / "sample.txt")
        assert "deadline" in msgs[0].content.lower()


class TestAutoDetect:
    def test_auto_json(self):
        msgs = load_messages(FIXTURES / "sample.json")
        assert len(msgs) > 0

    def test_auto_csv(self):
        msgs = load_messages(FIXTURES / "sample.csv")
        assert len(msgs) > 0

    def test_auto_txt(self):
        msgs = load_messages(FIXTURES / "sample.txt")
        assert len(msgs) > 0

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_messages(Path("/nonexistent/file.json"))
