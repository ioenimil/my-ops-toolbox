"""Exponential-backoff retry utility for async coroutines."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


async def with_retry(
    coro_fn: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    **kwargs: Any,
) -> Any:
    """Call coro_fn(*args, **kwargs) and retry on failure with exponential backoff.

    Retries up to max_attempts times. Backoff delays are base_delay * 2^attempt
    (1 s, 2 s, 4 s for the default base_delay of 1.0 and max_attempts of 3).
    Re-raises the final exception if all attempts are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await coro_fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                delay = base_delay * (2**attempt)
                logger.warning(
                    "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                    attempt + 1,
                    max_attempts,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.warning(
                    "Attempt %d/%d failed: %s. No more retries.",
                    attempt + 1,
                    max_attempts,
                    exc,
                )
    raise last_exc  # type: ignore[misc]
