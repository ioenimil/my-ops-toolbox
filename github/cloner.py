"""Core business logic for cloning and updating GitHub organisation repositories."""

from __future__ import annotations

import asyncio
import logging
from asyncio.subprocess import PIPE
from pathlib import Path

from github.exclusion import matches_any
from github.github_client import fetch_org_repos
from github.models import (
    ExclusionRule,
    Outcome,
    Repository,
    RunSummary,
    SyncResult,
)
from github.retry import with_retry

logger = logging.getLogger(__name__)


async def run_git_command(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a git command as an async subprocess and return its result.

    Returns a tuple of (returncode, stdout, stderr). Stderr is logged at
    DEBUG level; it is not surfaced to the user unless an error occurs.
    """
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=PIPE,
        stderr=PIPE,
        cwd=str(cwd),
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
    if stderr:
        logger.debug("git stderr [%s]: %s", " ".join(cmd[:3]), stderr)
    return process.returncode or 0, stdout, stderr


async def is_valid_git_repo(path: Path) -> bool:
    """Return True if path is the root of a valid local git repository."""
    returncode, _, _ = await run_git_command(
        ["git", "rev-parse", "--git-dir"], cwd=path
    )
    return returncode == 0


async def is_dirty(repo_dir: Path) -> bool:
    """Return True if the repository at repo_dir has uncommitted changes."""
    _, stdout, _ = await run_git_command(["git", "status", "--porcelain"], cwd=repo_dir)
    return bool(stdout)


async def clone_repo(
    repo: Repository,
    target_dir: Path,
    protocol: str,
    semaphore: asyncio.Semaphore,
) -> SyncResult:
    """Clone a single repository into target_dir, respecting the concurrency semaphore.

    Selects the HTTPS or SSH clone URL based on protocol. Retries up to three
    times with exponential backoff on failure. Returns a SyncResult indicating
    the outcome.
    """
    url = repo.clone_url if protocol == "https" else repo.ssh_url
    dest = str(target_dir / repo.name)

    async def _do_clone() -> tuple[int, str, str]:
        async with semaphore:
            return await run_git_command(["git", "clone", url, dest], cwd=target_dir)

    try:
        returncode, _, stderr = await with_retry(_do_clone)
        if returncode != 0:
            raise RuntimeError(f"git clone exited with code {returncode}: {stderr}")
        logger.debug("[cloned]    %s", repo.name)
        return SyncResult(repo_name=repo.name, outcome=Outcome.CLONED)
    except Exception as exc:
        logger.warning("[failed]    %s — %s", repo.name, exc)
        return SyncResult(repo_name=repo.name, outcome=Outcome.FAILED, error=str(exc))


async def update_repo(
    repo: Repository,
    repo_dir: Path,
    semaphore: asyncio.Semaphore,
) -> SyncResult:
    """Update an existing local repository to the latest remote state.

    Skips the update if the working tree has uncommitted changes, recording
    the result as SKIPPED_DIRTY. Compares HEAD before and after the pull to
    distinguish UPDATED from UP_TO_DATE. Retries on transient failures.
    """
    if await is_dirty(repo_dir):
        logger.warning(
            "[skipped]   %s — uncommitted changes detected; skipping update.",
            repo.name,
        )
        return SyncResult(repo_name=repo.name, outcome=Outcome.SKIPPED_DIRTY)

    async def _do_update() -> tuple[int, str, str]:
        async with semaphore:
            rc, _, err = await run_git_command(
                ["git", "fetch", "--prune"], cwd=repo_dir
            )
            if rc != 0:
                raise RuntimeError(f"git fetch failed (code {rc}): {err}")
            rc, _, err = await run_git_command(
                ["git", "pull", "--ff-only"], cwd=repo_dir
            )
            if rc != 0:
                raise RuntimeError(f"git pull failed (code {rc}): {err}")
            return rc, "", ""

    _, head_before, _ = await run_git_command(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir
    )

    try:
        await with_retry(_do_update)
    except Exception as exc:
        logger.warning("[failed]    %s — %s", repo.name, exc)
        return SyncResult(repo_name=repo.name, outcome=Outcome.FAILED, error=str(exc))

    _, head_after, _ = await run_git_command(["git", "rev-parse", "HEAD"], cwd=repo_dir)

    if head_before != head_after:
        logger.debug("[updated]   %s", repo.name)
        return SyncResult(repo_name=repo.name, outcome=Outcome.UPDATED)

    logger.debug("[up-to-date] %s", repo.name)
    return SyncResult(repo_name=repo.name, outcome=Outcome.UP_TO_DATE)


async def sync_organisation(
    org: str,
    target_dir: Path,
    token: str,
    rules: list[ExclusionRule] | None = None,
    prefix_includes: list[str] | None = None,
    suffix_includes: list[str] | None = None,
    regex_includes: list[str] | None = None,
    filter_config=None,
    protocol: str = "https",
    max_concurrent: int = 5,
    verbose: bool = False,
) -> list[SyncResult]:
    """Synchronise all repositories of a GitHub organisation to a local directory.

    Fetches the full repository list via the GitHub GraphQL API, applies any
    exclusion rules, then clones missing repositories and updates existing ones
    in parallel, bounded by max_concurrent. Returns a list of SyncResult
    instances covering every repository encountered.
    """
    if rules is None:
        rules = []

    target_dir.mkdir(parents=True, exist_ok=True)
    repos = await fetch_org_repos(org, token)

    from github.filtering import filter_repositories

    # Apply complex inclusion/exclusion if filtering elements are present
    if prefix_includes or suffix_includes or regex_includes or filter_config:
        repos = filter_repositories(
            repos,
            prefix_includes=prefix_includes,
            suffix_includes=suffix_includes,
            regex_includes=regex_includes,
            config=filter_config,
        )

    logger.info("Syncing organisation: %s (%d repositories)", org, len(repos))

    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[SyncResult] = []
    clone_tasks: list[asyncio.Task[SyncResult]] = []
    update_tasks: list[asyncio.Task[SyncResult]] = []

    for repo in repos:
        if matches_any(repo.name, rules):
            logger.debug("[excluded]  %s", repo.name)
            results.append(
                SyncResult(repo_name=repo.name, outcome=Outcome.SKIPPED_EXCLUDED)
            )
            continue

        repo_dir = target_dir / repo.name

        if repo_dir.exists():
            if not await is_valid_git_repo(repo_dir):
                logger.warning(
                    "[skipped]   %s — directory exists but is not a git repository.",
                    repo.name,
                )
                results.append(
                    SyncResult(
                        repo_name=repo.name,
                        outcome=Outcome.SKIPPED_DIRTY,
                        error="directory exists but is not a git repository",
                    )
                )
                continue
            update_tasks.append(
                asyncio.create_task(update_repo(repo, repo_dir, semaphore))
            )
        else:
            clone_tasks.append(
                asyncio.create_task(clone_repo(repo, target_dir, protocol, semaphore))
            )

    gathered = await asyncio.gather(*clone_tasks, *update_tasks)
    results.extend(gathered)

    if verbose:
        for result in gathered:
            label = result.outcome.name.lower().replace("_", " ")
            suffix = f" — {result.error}" if result.error else ""
            logger.info("[%s] %s%s", label, result.repo_name, suffix)

    return results


def build_summary(results: list[SyncResult]) -> RunSummary:
    """Aggregate a list of SyncResults into a RunSummary with per-outcome counts."""
    summary = RunSummary()
    for result in results:
        match result.outcome:
            case Outcome.CLONED:
                summary.cloned += 1
            case Outcome.UPDATED:
                summary.updated += 1
            case Outcome.UP_TO_DATE:
                summary.up_to_date += 1
            case Outcome.SKIPPED_EXCLUDED:
                summary.skipped_excluded += 1
            case Outcome.SKIPPED_DIRTY:
                summary.skipped_dirty += 1
            case Outcome.FAILED:
                summary.failed += 1
    return summary


def format_summary(summary: RunSummary) -> str:
    """Format a RunSummary as a human-readable text table."""
    lines = [
        "",
        "Summary",
        "-------",
        f"Cloned:           {summary.cloned:>4}",
        f"Updated:          {summary.updated:>4}",
        f"Up to date:       {summary.up_to_date:>4}",
        f"Skipped (excl.):  {summary.skipped_excluded:>4}",
        f"Skipped (dirty):  {summary.skipped_dirty:>4}",
        f"Failed:           {summary.failed:>4}",
        f"Total:            {summary.total:>4}",
    ]
    return "\n".join(lines)
