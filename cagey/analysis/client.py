"""Thin wrapper around the Anthropic client with retry and usage tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from cagey.config import CageySettings


@dataclass
class UsageSummary:
    """Running token-usage totals across a batch of analysis calls."""

    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    failures: int = 0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, input_tokens: int, output_tokens: int) -> None:
        with self._lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.calls += 1

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


_RETRYABLE = (
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
)


def _with_retry(fn):
    """Exponential backoff retry decorator for transient Anthropic failures."""
    return retry(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        reraise=True,
    )(fn)


class CageyClient:
    """Holds both sync and async Anthropic clients, plus a UsageSummary accumulator."""

    def __init__(self, settings: CageySettings, model: str | None = None):
        self.settings = settings
        self.model = model or settings.default_model
        self.max_tokens = settings.max_tokens_per_call
        self.usage = UsageSummary()
        self._sync: anthropic.Anthropic | None = None
        self._async: anthropic.AsyncAnthropic | None = None

    @property
    def sync(self) -> anthropic.Anthropic:
        if self._sync is None:
            self._sync = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        return self._sync

    @property
    def async_(self) -> anthropic.AsyncAnthropic:
        if self._async is None:
            self._async = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        return self._async

    @_with_retry
    def create_message(self, **kwargs):
        return self.sync.messages.create(**kwargs)

    @_with_retry
    async def acreate_message(self, **kwargs):
        return await self.async_.messages.create(**kwargs)
