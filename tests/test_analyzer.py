"""Tests for Analyzer — all Claude API calls are mocked."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cagey.analysis.analyzer import Analyzer
from cagey.analysis.models import SubAuditionCategory
from cagey.ingest.base import Message


def _make_msg(content: str = "Test message", author: str = "Alice") -> Message:
    return Message(
        author=author,
        timestamp=datetime.now(tz=timezone.utc),
        content=content,
        channel="general",
    )


def _mock_tool_response(
    sentiment_label: str = "negative",
    sentiment_score: float = -0.7,
    emotional_tone: str = "frustrated",
    category: str = "passive_aggression",
    confidence: float = 0.85,
    explanation: str = "Backhanded praise.",
    trigger: str = "interesting approach",
    summary: str = "Implies disapproval while appearing cooperative.",
):
    """Build a fake anthropic Messages response with a tool_use block."""
    tool_input = {
        "sentiment": {
            "label": sentiment_label,
            "score": sentiment_score,
            "emotional_tone": emotional_tone,
        },
        "sub_auditions": [
            {
                "category": category,
                "confidence": confidence,
                "explanation": explanation,
                "quoted_trigger": trigger,
            }
        ],
        "summary": summary,
    }
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "record_analysis"
    tool_block.input = tool_input

    usage = MagicMock()
    usage.input_tokens = 120
    usage.output_tokens = 80

    response = MagicMock()
    response.content = [tool_block]
    response.usage = usage
    return response


class TestAnalyzeMessage:
    def _make_analyzer(self):
        from cagey.analysis.client import CageyClient
        from cagey.config import CageySettings

        settings = CageySettings(
            ANTHROPIC_API_KEY="sk-test",
            CAGEY_MODEL="claude-opus-4-6",
        )
        client = CageyClient(settings)
        return Analyzer(client)

    def test_returns_analysis_result(self):
        analyzer = self._make_analyzer()
        fake_response = _mock_tool_response()

        with patch.object(analyzer.client, "create_message", return_value=fake_response):
            result = analyzer.analyze_message(_make_msg())

        assert result.error is None
        assert result.sentiment.label == "negative"
        assert abs(result.sentiment.score - (-0.7)) < 1e-6
        assert result.sub_auditions[0].category == SubAuditionCategory.PASSIVE_AGGRESSION
        assert result.sub_auditions[0].confidence == pytest.approx(0.85)
        assert result.tokens_used == 200

    def test_handles_api_failure(self):
        analyzer = self._make_analyzer()

        with patch.object(
            analyzer.client, "create_message", side_effect=Exception("API error")
        ):
            result = analyzer.analyze_message(_make_msg())

        assert result.error is not None
        assert "API error" in result.error

    def test_handles_missing_tool_use(self):
        analyzer = self._make_analyzer()

        text_block = MagicMock()
        text_block.type = "text"

        response = MagicMock()
        response.content = [text_block]

        with patch.object(analyzer.client, "create_message", return_value=response):
            result = analyzer.analyze_message(_make_msg())

        assert result.error is not None

    def test_usage_accumulated(self):
        analyzer = self._make_analyzer()
        fake = _mock_tool_response()

        with patch.object(analyzer.client, "create_message", return_value=fake):
            analyzer.analyze_message(_make_msg())
            analyzer.analyze_message(_make_msg())

        assert analyzer.client.usage.calls == 2
        assert analyzer.client.usage.input_tokens == 240


@pytest.mark.asyncio
class TestAnalyzeBatch:
    def _make_analyzer(self):
        from cagey.analysis.client import CageyClient
        from cagey.config import CageySettings

        settings = CageySettings(
            ANTHROPIC_API_KEY="sk-test",
            CAGEY_MODEL="claude-opus-4-6",
        )
        client = CageyClient(settings)
        return Analyzer(client)

    async def test_batch_returns_all(self):
        analyzer = self._make_analyzer()
        msgs = [_make_msg(f"message {i}") for i in range(3)]
        fake = _mock_tool_response()

        with patch.object(
            analyzer.client, "acreate_message", new=AsyncMock(return_value=fake)
        ):
            results = await analyzer.analyze_batch(msgs, concurrency=2)

        assert len(results) == 3
        assert all(r.error is None for r in results)

    async def test_batch_partial_failure(self):
        analyzer = self._make_analyzer()
        msgs = [_make_msg(f"message {i}") for i in range(3)]
        fake = _mock_tool_response()

        call_count = 0

        async def flaky(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Transient error")
            return fake

        with patch.object(analyzer.client, "acreate_message", new=flaky):
            results = await analyzer.analyze_batch(msgs, concurrency=1)

        assert len(results) == 3
        errors = [r for r in results if r.error]
        non_errors = [r for r in results if not r.error]
        assert len(errors) == 1
        assert len(non_errors) == 2
