"""Unit tests for github.retry."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, call, patch

import pytest

from github.retry import with_retry


@pytest.mark.asyncio
async def test_succeeds_on_first_attempt() -> None:
    """with_retry returns the result immediately when the coroutine succeeds."""
    coro = AsyncMock(return_value="ok")
    result = await with_retry(coro, max_attempts=3)
    assert result == "ok"
    coro.assert_awaited_once()


@pytest.mark.asyncio
async def test_retries_once_on_failure_then_succeeds() -> None:
    """with_retry retries after a single failure and returns on the second attempt."""
    coro = AsyncMock(side_effect=[RuntimeError("blip"), "ok"])

    with patch("github.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await with_retry(coro, max_attempts=3, base_delay=1.0)

    assert result == "ok"
    assert coro.await_count == 2
    mock_sleep.assert_awaited_once_with(1.0)


@pytest.mark.asyncio
async def test_exhausts_all_retries_and_reraises() -> None:
    """with_retry raises the final exception after max_attempts failures."""
    exc = RuntimeError("persistent failure")
    coro = AsyncMock(side_effect=exc)

    with patch("github.retry.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="persistent failure"):
            await with_retry(coro, max_attempts=3)

    assert coro.await_count == 3


@pytest.mark.asyncio
async def test_backoff_delays_are_exponential() -> None:
    """with_retry sleeps for base_delay * 2^attempt between retries."""
    coro = AsyncMock(side_effect=[RuntimeError("e"), RuntimeError("e"), "ok"])

    with patch("github.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await with_retry(coro, max_attempts=3, base_delay=2.0)

    assert mock_sleep.await_args_list == [call(2.0), call(4.0)]


@pytest.mark.asyncio
async def test_single_attempt_reraises_immediately() -> None:
    """with_retry with max_attempts=1 raises without sleeping."""
    coro = AsyncMock(side_effect=ValueError("instant fail"))

    with patch("github.retry.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with pytest.raises(ValueError, match="instant fail"):
            await with_retry(coro, max_attempts=1)

    mock_sleep.assert_not_awaited()
