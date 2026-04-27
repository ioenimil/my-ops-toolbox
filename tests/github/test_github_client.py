"""Unit tests for github.github_client."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from github.github_client import resolve_token


class TestResolveToken:
    """Tests for resolve_token."""

    def test_returns_github_token_env_var_when_set(self) -> None:
        """resolve_token returns the GITHUB_TOKEN env var when present."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "tok_abc123"}):
            token = resolve_token()
        assert token == "tok_abc123"

    def test_calls_gh_cli_when_env_var_absent(self) -> None:
        """resolve_token falls back to gh auth token when GITHUB_TOKEN is not set."""
        env_without_token = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        mock_result = MagicMock()
        mock_result.stdout = "gh_token_xyz\n"

        with patch.dict(os.environ, env_without_token, clear=True):
            with patch("github.github_client.subprocess.run", return_value=mock_result):
                token = resolve_token()

        assert token == "gh_token_xyz"

    def test_raises_system_exit_when_both_sources_absent(self) -> None:
        """resolve_token raises SystemExit(1) when no token is available."""
        env_without_token = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        mock_result = MagicMock()
        mock_result.stdout = ""

        with patch.dict(os.environ, env_without_token, clear=True):
            with patch("github.github_client.subprocess.run", return_value=mock_result):
                with pytest.raises(SystemExit) as exc_info:
                    resolve_token()

        assert exc_info.value.code == 1

    def test_raises_system_exit_when_gh_not_found(self) -> None:
        """resolve_token raises SystemExit(1) when gh CLI is not installed."""
        env_without_token = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}

        with patch.dict(os.environ, env_without_token, clear=True):
            with patch(
                "github.github_client.subprocess.run",
                side_effect=FileNotFoundError("gh not found"),
            ):
                with pytest.raises(SystemExit) as exc_info:
                    resolve_token()

        assert exc_info.value.code == 1


class TestHandleRateLimit:
    """Tests for _handle_rate_limit pause logic."""

    @pytest.mark.asyncio
    async def test_no_sleep_when_remaining_above_threshold(self) -> None:
        """_handle_rate_limit does not sleep when remaining >= threshold."""
        from github.github_client import _handle_rate_limit

        rate_limit = {
            "remaining": 1000,
            "resetAt": "2026-04-27T15:00:00Z",
        }
        with patch("github.github_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await _handle_rate_limit(rate_limit)

        mock_sleep.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sleeps_when_remaining_below_threshold(self) -> None:
        """_handle_rate_limit sleeps when remaining < 50."""
        from datetime import datetime, timezone

        from github.github_client import _handle_rate_limit

        future_reset = datetime.now(tz=timezone.utc).replace(
            microsecond=0
        ).isoformat().replace("+00:00", "Z")

        rate_limit = {"remaining": 10, "resetAt": future_reset}

        with patch("github.github_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await _handle_rate_limit(rate_limit)

        mock_sleep.assert_awaited_once()
