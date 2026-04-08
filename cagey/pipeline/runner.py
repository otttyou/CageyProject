"""Orchestrate the full ingest → analyze → sort pipeline."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

from cagey.analysis.analyzer import Analyzer
from cagey.analysis.client import CageyClient, UsageSummary
from cagey.analysis.models import AnalysisResult
from cagey.config import CageySettings
from cagey.ingest import load_messages
from cagey.ingest.base import Message


class PipelineRunner:
    """End-to-end runner: parse file → call Claude → return results."""

    def __init__(self, settings: CageySettings, model: str | None = None):
        self.settings = settings
        self.client = CageyClient(settings, model=model)
        self.analyzer = Analyzer(self.client)

    @property
    def usage(self) -> UsageSummary:
        return self.client.usage

    def run(
        self,
        input_path: Path,
        format: str = "auto",
        concurrency: int | None = None,
        on_progress: Callable[[AnalysisResult], None] | None = None,
    ) -> list[AnalysisResult]:
        """Parse the chat file and analyze every message with Claude."""
        messages = load_messages(input_path, format=format)
        return asyncio.run(
            self.analyzer.analyze_batch(
                messages,
                concurrency=concurrency or self.settings.default_concurrency,
                on_progress=on_progress,
            )
        )

    def run_with_progress(
        self,
        input_path: Path,
        format: str = "auto",
        concurrency: int | None = None,
    ) -> list[AnalysisResult]:
        """Like run(), but shows a rich progress bar while analyzing."""
        messages = load_messages(input_path, format=format)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Analyzing messages…", total=len(messages))

            def on_done(result: AnalysisResult) -> None:
                progress.advance(task)

            return asyncio.run(
                self.analyzer.analyze_batch(
                    messages,
                    concurrency=concurrency or self.settings.default_concurrency,
                    on_progress=on_done,
                )
            )

    @staticmethod
    def save_report(results: list[AnalysisResult], output_dir: Path) -> Path:
        """Serialize results to JSON and return the file path."""
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = output_dir / f"analysis_report_{ts}.json"
        data = [r.model_dump(mode="json") for r in results]
        out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return out

    @staticmethod
    def load_report(path: Path) -> list[AnalysisResult]:
        """Load a previously saved JSON report."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [AnalysisResult.model_validate(item) for item in raw]

    @staticmethod
    def validate_only(input_path: Path, format: str = "auto") -> list[Message]:
        """Parse the file and return messages without calling the API."""
        return load_messages(input_path, format=format)
