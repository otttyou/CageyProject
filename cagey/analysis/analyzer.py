"""Run Claude-powered analysis on individual messages or batches."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable

from cagey.analysis.client import CageyClient
from cagey.analysis.models import (
    AnalysisResult,
    SentimentScore,
    SerializedMessage,
    SubAudition,
    SubAuditionCategory,
)
from cagey.analysis.prompts import SYSTEM_PROMPT, TOOL_NAME, TOOL_SCHEMA, render_user_message
from cagey.ingest.base import Message


class Analyzer:
    """Analyze chat messages using Claude with structured tool-call output."""

    def __init__(self, client: CageyClient):
        self.client = client

    # ------------------------------------------------------------------ sync

    def analyze_message(self, msg: Message) -> AnalysisResult:
        """Analyze a single message synchronously."""
        user_text = render_user_message(
            author=msg.author,
            timestamp=msg.timestamp.isoformat(),
            content=msg.content,
            channel=msg.channel,
        )

        try:
            response = self.client.create_message(
                model=self.client.model,
                max_tokens=self.client.max_tokens,
                # Adaptive thinking lets Claude spend more reasoning on tricky
                # messages and less on obvious ones. Default for Opus 4.6.
                thinking={"type": "adaptive"},
                # Cache the (large, stable) system prompt across the batch.
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=[TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=[{"role": "user", "content": user_text}],
            )
        except Exception as exc:  # noqa: BLE001 — we want to surface any failure as an error result
            self.client.usage.record_failure()
            return _error_result(msg, self.client.model, str(exc))

        return self._parse_response(msg, response)

    # ----------------------------------------------------------------- async

    async def analyze_batch(
        self,
        messages: list[Message],
        concurrency: int | None = None,
        on_progress: Callable[[AnalysisResult], None] | None = None,
    ) -> list[AnalysisResult]:
        """Analyze many messages concurrently with a semaphore."""
        concurrency = concurrency or self.client.settings.default_concurrency
        semaphore = asyncio.Semaphore(concurrency)

        async def _one(msg: Message) -> AnalysisResult:
            async with semaphore:
                result = await self._analyze_one_async(msg)
                if on_progress is not None:
                    on_progress(result)
                return result

        return await asyncio.gather(*(_one(m) for m in messages))

    async def _analyze_one_async(self, msg: Message) -> AnalysisResult:
        user_text = render_user_message(
            author=msg.author,
            timestamp=msg.timestamp.isoformat(),
            content=msg.content,
            channel=msg.channel,
        )
        try:
            response = await self.client.acreate_message(
                model=self.client.model,
                max_tokens=self.client.max_tokens,
                thinking={"type": "adaptive"},
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=[TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=[{"role": "user", "content": user_text}],
            )
        except Exception as exc:  # noqa: BLE001
            self.client.usage.record_failure()
            return _error_result(msg, self.client.model, str(exc))

        return self._parse_response(msg, response)

    # ----------------------------------------------------------- response parsing

    def _parse_response(self, msg: Message, response: Any) -> AnalysisResult:
        # Extract the tool_use block — we forced tool_choice so it must exist.
        tool_use_block = None
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == TOOL_NAME:
                tool_use_block = block
                break

        if tool_use_block is None:
            self.client.usage.record_failure()
            return _error_result(
                msg,
                self.client.model,
                "Claude did not call the record_analysis tool.",
            )

        # Record token usage.
        usage = getattr(response, "usage", None)
        in_tok = getattr(usage, "input_tokens", 0) if usage else 0
        out_tok = getattr(usage, "output_tokens", 0) if usage else 0
        self.client.usage.record(in_tok, out_tok)

        raw = tool_use_block.input
        try:
            sentiment = SentimentScore(**raw["sentiment"])
            sub_auditions = [SubAudition(**sa) for sa in raw.get("sub_auditions", [])]
            summary = str(raw.get("summary", ""))
        except (KeyError, TypeError, ValueError) as exc:
            return _error_result(msg, self.client.model, f"Invalid tool output: {exc}")

        if not sub_auditions:
            sub_auditions = [
                SubAudition(
                    category=SubAuditionCategory.NONE,
                    confidence=0.0,
                    explanation="No implicit subtext detected.",
                    quoted_trigger="",
                )
            ]

        return AnalysisResult(
            message=SerializedMessage.from_message(msg),
            sentiment=sentiment,
            sub_auditions=sub_auditions,
            summary=summary,
            analyzed_at=datetime.now(tz=timezone.utc),
            model_used=self.client.model,
            tokens_used=in_tok + out_tok,
        )


def _error_result(msg: Message, model: str, error: str) -> AnalysisResult:
    return AnalysisResult(
        message=SerializedMessage.from_message(msg),
        sentiment=SentimentScore(label="neutral", score=0.0, emotional_tone="unknown"),
        sub_auditions=[
            SubAudition(
                category=SubAuditionCategory.NONE,
                confidence=0.0,
                explanation=f"Analysis failed: {error}",
                quoted_trigger="",
            )
        ],
        summary="(analysis failed)",
        analyzed_at=datetime.now(tz=timezone.utc),
        model_used=model,
        tokens_used=0,
        error=error,
    )
