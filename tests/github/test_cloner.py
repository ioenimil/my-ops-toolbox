"""Unit tests for github.cloner business logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from github.cloner import build_summary, format_summary, is_dirty, is_valid_git_repo
from github.models import Outcome, RunSummary, SyncResult


class TestIsValidGitRepo:
    """Tests for is_valid_git_repo."""

    @pytest.mark.asyncio
    async def test_returns_true_when_git_rev_parse_succeeds(self, tmp_path: Path) -> None:
        """is_valid_git_repo returns True when git rev-parse exits 0."""
        with patch(
            "github.cloner.run_git_command",
            new_callable=AsyncMock,
            return_value=(0, ".git", ""),
        ):
            result = await is_valid_git_repo(tmp_path)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_git_rev_parse_fails(self, tmp_path: Path) -> None:
        """is_valid_git_repo returns False when git rev-parse exits non-zero."""
        with patch(
            "github.cloner.run_git_command",
            new_callable=AsyncMock,
            return_value=(128, "", "not a git repository"),
        ):
            result = await is_valid_git_repo(tmp_path)
        assert result is False


class TestIsDirty:
    """Tests for is_dirty."""

    @pytest.mark.asyncio
    async def test_returns_true_when_git_status_has_output(self, tmp_path: Path) -> None:
        """is_dirty returns True when git status --porcelain produces output."""
        with patch(
            "github.cloner.run_git_command",
            new_callable=AsyncMock,
            return_value=(0, " M some_file.py", ""),
        ):
            assert await is_dirty(tmp_path) is True

    @pytest.mark.asyncio
    async def test_returns_false_when_git_status_is_empty(self, tmp_path: Path) -> None:
        """is_dirty returns False when git status --porcelain produces no output."""
        with patch(
            "github.cloner.run_git_command",
            new_callable=AsyncMock,
            return_value=(0, "", ""),
        ):
            assert await is_dirty(tmp_path) is False


class TestBuildSummary:
    """Tests for build_summary."""

    def test_counts_all_outcome_types(self) -> None:
        """build_summary correctly tallies each Outcome member."""
        results = [
            SyncResult("a", Outcome.CLONED),
            SyncResult("b", Outcome.CLONED),
            SyncResult("c", Outcome.UPDATED),
            SyncResult("d", Outcome.UP_TO_DATE),
            SyncResult("e", Outcome.SKIPPED_EXCLUDED),
            SyncResult("f", Outcome.SKIPPED_DIRTY),
            SyncResult("g", Outcome.FAILED, error="oops"),
        ]
        summary = build_summary(results)
        assert summary.cloned == 2
        assert summary.updated == 1
        assert summary.up_to_date == 1
        assert summary.skipped_excluded == 1
        assert summary.skipped_dirty == 1
        assert summary.failed == 1
        assert summary.total == 7

    def test_empty_results_produce_zero_summary(self) -> None:
        """build_summary with no results returns a summary with all zeros."""
        summary = build_summary([])
        assert summary.total == 0
        assert isinstance(summary, RunSummary)


class TestFormatSummary:
    """Tests for format_summary."""

    def test_format_includes_all_fields(self) -> None:
        """format_summary output contains all six count labels."""
        summary = RunSummary(cloned=1, updated=2, up_to_date=3)
        output = format_summary(summary)
        assert "Cloned:" in output
        assert "Updated:" in output
        assert "Up to date:" in output
        assert "Skipped (excl.):" in output
        assert "Skipped (dirty):" in output
        assert "Failed:" in output
        assert "Total:" in output

    def test_format_shows_correct_counts(self) -> None:
        """format_summary renders the numeric values from the summary."""
        summary = RunSummary(cloned=5, failed=2)
        output = format_summary(summary)
        assert "5" in output
        assert "2" in output
