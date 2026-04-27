"""Unit tests for github.models."""

from github.models import (
    Outcome,
    RunSummary,
    SyncResult,
)


def test_outcome_has_all_members() -> None:
    """Outcome enum must expose exactly the six defined members."""
    expected = {
        "CLONED",
        "UPDATED",
        "UP_TO_DATE",
        "SKIPPED_EXCLUDED",
        "SKIPPED_DIRTY",
        "FAILED",
    }
    assert {m.name for m in Outcome} == expected


def test_sync_result_stores_outcome_and_no_error() -> None:
    """SyncResult stores repo name and outcome; error defaults to None."""
    result = SyncResult(repo_name="my-repo", outcome=Outcome.CLONED)
    assert result.repo_name == "my-repo"
    assert result.outcome is Outcome.CLONED
    assert result.error is None


def test_sync_result_stores_error_message() -> None:
    """SyncResult with FAILED outcome preserves the error string."""
    result = SyncResult(repo_name="bad-repo", outcome=Outcome.FAILED, error="timeout")
    assert result.error == "timeout"


def test_run_summary_total_equals_sum_of_counts() -> None:
    """RunSummary.total must equal the arithmetic sum of all count fields."""
    summary = RunSummary(
        cloned=2,
        updated=3,
        up_to_date=5,
        skipped_excluded=1,
        skipped_dirty=1,
        failed=0,
    )
    assert summary.total == 12


def test_build_summary_counts_each_outcome() -> None:
    """build_summary produces correct per-outcome counts from a list of results."""
    from github.cloner import build_summary

    results = [
        SyncResult("a", Outcome.CLONED),
        SyncResult("b", Outcome.CLONED),
        SyncResult("c", Outcome.UPDATED),
        SyncResult("d", Outcome.UP_TO_DATE),
        SyncResult("e", Outcome.SKIPPED_EXCLUDED),
        SyncResult("f", Outcome.SKIPPED_DIRTY),
        SyncResult("g", Outcome.FAILED, error="err"),
    ]
    summary = build_summary(results)
    assert summary.cloned == 2
    assert summary.updated == 1
    assert summary.up_to_date == 1
    assert summary.skipped_excluded == 1
    assert summary.skipped_dirty == 1
    assert summary.failed == 1
    assert summary.total == 7


def test_run_summary_total_zero_when_empty() -> None:
    """RunSummary with all zero counts has total of zero."""
    assert RunSummary().total == 0
