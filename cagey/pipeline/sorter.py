"""Sorting, filtering, and aggregation for AnalysisResult collections."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

from cagey.analysis.models import AnalysisResult, SubAuditionCategory


class SortKey(str, Enum):
    AUTHOR = "author"
    SENTIMENT_SCORE = "sentiment"
    TIMESTAMP = "time"
    SUB_AUDITION = "subaudition"
    CONFIDENCE = "confidence"


@dataclass
class AuthorStats:
    author: str
    message_count: int = 0
    avg_sentiment: float = 0.0
    dominant_sub_audition: SubAuditionCategory = SubAuditionCategory.NONE
    sub_audition_counts: Counter = field(default_factory=Counter)
    sentiment_distribution: dict[str, int] = field(default_factory=dict)
    total_confidence: float = 0.0


class Sorter:
    """Sort, filter, and aggregate AnalysisResult lists."""

    @staticmethod
    def sort(
        results: list[AnalysisResult],
        primary: SortKey = SortKey.SENTIMENT_SCORE,
        secondary: SortKey | None = None,
        ascending: bool = False,
        filter_author: str | None = None,
        filter_category: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[AnalysisResult]:
        filtered = results

        if filter_author:
            fa = filter_author.lower()
            filtered = [r for r in filtered if fa in r.message.author.lower()]

        if filter_category:
            fc = filter_category.lower()
            filtered = [
                r for r in filtered
                if any(sa.category.value == fc for sa in r.sub_auditions)
            ]

        if min_confidence > 0.0:
            filtered = [
                r for r in filtered
                if any(sa.confidence >= min_confidence for sa in r.sub_auditions)
            ]

        def sort_key(r: AnalysisResult):
            k1 = _key_for(r, primary)
            k2 = _key_for(r, secondary) if secondary else ""
            return (k1, k2)

        return sorted(filtered, key=sort_key, reverse=not ascending)

    @staticmethod
    def aggregate_by_author(results: list[AnalysisResult]) -> dict[str, AuthorStats]:
        stats: dict[str, AuthorStats] = {}

        for r in results:
            author = r.message.author
            if author not in stats:
                stats[author] = AuthorStats(author=author)
            s = stats[author]
            s.message_count += 1
            s.avg_sentiment += r.sentiment.score

            label = r.sentiment.label
            s.sentiment_distribution[label] = s.sentiment_distribution.get(label, 0) + 1

            for sa in r.sub_auditions:
                if sa.category != SubAuditionCategory.NONE:
                    s.sub_audition_counts[sa.category.value] += 1

        for s in stats.values():
            if s.message_count:
                s.avg_sentiment /= s.message_count
            if s.sub_audition_counts:
                s.dominant_sub_audition = SubAuditionCategory(
                    s.sub_audition_counts.most_common(1)[0][0]
                )

        return stats


def _key_for(r: AnalysisResult, key: SortKey) -> float | str:
    if key == SortKey.AUTHOR:
        return r.message.author.lower()
    if key == SortKey.SENTIMENT_SCORE:
        return r.sentiment.score
    if key == SortKey.TIMESTAMP:
        return r.message.timestamp.isoformat()
    if key == SortKey.SUB_AUDITION:
        primary = r.primary_sub_audition
        return primary.category.value if primary else "zzz_none"
    if key == SortKey.CONFIDENCE:
        primary = r.primary_sub_audition
        return primary.confidence if primary else 0.0
    return 0.0
