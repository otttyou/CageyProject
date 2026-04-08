"""Pipeline: orchestrate ingest → analyze → collect results."""

from cagey.pipeline.runner import PipelineRunner
from cagey.pipeline.sorter import AuthorStats, SortKey, Sorter

__all__ = ["PipelineRunner", "Sorter", "SortKey", "AuthorStats"]
