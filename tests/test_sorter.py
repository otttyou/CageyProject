"""Tests for the Sorter and AuthorStats aggregation."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cagey.analysis.models import (
    AnalysisResult,
    SentimentScore,
    SerializedMessage,
    SubAudition,
    SubAuditionCategory,
)
from cagey.ingest.base import Message
from cagey.pipeline.sorter import SortKey, Sorter


def _make_result(
    author: str,
    score: float,
    label: str = "neutral",
    category: SubAuditionCategory = SubAuditionCategory.NONE,
    confidence: float = 0.0,
    content: str = "test message",
) -> AnalysisResult:
    msg = Message(author=author, timestamp=datetime.now(tz=timezone.utc), content=content)
    return AnalysisResult(
        message=SerializedMessage.from_message(msg),
        sentiment=SentimentScore(label=label, score=score, emotional_tone="neutral"),
        sub_auditions=[
            SubAudition(
                category=category,
                confidence=confidence,
                explanation="test",
                quoted_trigger="test",
            )
        ],
        summary="test",
        model_used="test-model",
    )


RESULTS = [
    _make_result("Alice", -0.8, "negative", SubAuditionCategory.PASSIVE_AGGRESSION, 0.9),
    _make_result("Bob", 0.5, "positive", SubAuditionCategory.URGENCY_SIGNALING, 0.7),
    _make_result("Carol", 0.9, "positive", SubAuditionCategory.NONE, 0.0),
    _make_result("Alice", 0.2, "positive", SubAuditionCategory.DISMISSAL, 0.6),
    _make_result("Dave", -0.3, "negative", SubAuditionCategory.DEFLECTION, 0.5),
]


class TestSort:
    def test_sort_by_sentiment_descending(self):
        sorted_r = Sorter.sort(RESULTS, primary=SortKey.SENTIMENT_SCORE, ascending=False)
        scores = [r.sentiment.score for r in sorted_r]
        assert scores == sorted(scores, reverse=True)

    def test_sort_by_sentiment_ascending(self):
        sorted_r = Sorter.sort(RESULTS, primary=SortKey.SENTIMENT_SCORE, ascending=True)
        scores = [r.sentiment.score for r in sorted_r]
        assert scores == sorted(scores)

    def test_sort_by_author(self):
        sorted_r = Sorter.sort(RESULTS, primary=SortKey.AUTHOR, ascending=True)
        authors = [r.message.author for r in sorted_r]
        assert authors == sorted(authors)

    def test_filter_author(self):
        filtered = Sorter.sort(RESULTS, filter_author="Alice")
        assert all(r.message.author == "Alice" for r in filtered)
        assert len(filtered) == 2

    def test_filter_category(self):
        filtered = Sorter.sort(RESULTS, filter_category="passive_aggression")
        assert len(filtered) == 1
        assert filtered[0].message.author == "Alice"

    def test_min_confidence(self):
        filtered = Sorter.sort(RESULTS, min_confidence=0.8)
        assert all(
            any(sa.confidence >= 0.8 for sa in r.sub_auditions) for r in filtered
        )

    def test_empty_results(self):
        assert Sorter.sort([]) == []


class TestAggregateByAuthor:
    def test_author_count(self):
        stats = Sorter.aggregate_by_author(RESULTS)
        assert set(stats.keys()) == {"Alice", "Bob", "Carol", "Dave"}

    def test_alice_message_count(self):
        stats = Sorter.aggregate_by_author(RESULTS)
        assert stats["Alice"].message_count == 2

    def test_avg_sentiment(self):
        stats = Sorter.aggregate_by_author(RESULTS)
        alice_avg = (-0.8 + 0.2) / 2
        assert abs(stats["Alice"].avg_sentiment - alice_avg) < 1e-9

    def test_dominant_sub_audition(self):
        stats = Sorter.aggregate_by_author(RESULTS)
        # Alice has passive_aggression + dismissal, both count 1 — just check it's set
        assert stats["Alice"].dominant_sub_audition in (
            SubAuditionCategory.PASSIVE_AGGRESSION,
            SubAuditionCategory.DISMISSAL,
        )

    def test_sentiment_distribution(self):
        stats = Sorter.aggregate_by_author(RESULTS)
        assert stats["Bob"].sentiment_distribution.get("positive", 0) == 1
