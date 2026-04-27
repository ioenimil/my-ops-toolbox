"""Async GitHub GraphQL client for listing organisation repositories."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
from datetime import datetime, timezone

import httpx

from github.models import Repository
from github.retry import with_retry

logger = logging.getLogger(__name__)

_GRAPHQL_ENDPOINT = "https://api.github.com/graphql"

_ORG_REPOS_QUERY = """
query OrgRepos($org: String!, $after: String) {
  organization(login: $org) {
    repositories(
      first: 100
      after: $after
      orderBy: { field: NAME, direction: ASC }
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        url
        sshUrl
        isFork
        isArchived
        defaultBranchRef {
          name
        }
      }
    }
  }
  rateLimit {
    cost
    remaining
    resetAt
  }
}
"""

_RATE_LIMIT_THRESHOLD = 50
_RATE_LIMIT_BUFFER_SECONDS = 5


def resolve_token() -> str:
    """Resolve a GitHub API token from the environment or the gh CLI token store.

    Reads GITHUB_TOKEN first. Falls back to running ``gh auth token`` if the
    environment variable is not set. Exits with a non-zero code and an
    actionable error message if neither source yields a token.
    """
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        logger.debug("GitHub token resolved from GITHUB_TOKEN environment variable.")
        return token

    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=False,
        )
        token = result.stdout.strip()
    except FileNotFoundError:
        token = ""

    if token:
        logger.debug("GitHub token resolved from gh CLI token store.")
        return token

    logger.error(
        "No GitHub token found. "
        "Set the GITHUB_TOKEN environment variable or run `gh auth login` to authenticate."
    )
    raise SystemExit(1)


async def _fetch_page(
    client: httpx.AsyncClient,
    org: str,
    cursor: str | None,
) -> dict:
    """Fetch a single page of organisation repositories from the GraphQL API."""
    variables: dict[str, str | None] = {"org": org, "after": cursor}
    response = await client.post(
        _GRAPHQL_ENDPOINT,
        json={"query": _ORG_REPOS_QUERY, "variables": variables},
    )
    if response.status_code == 401:
        logger.error(
            "GitHub API returned 401 Unauthorized. "
            "Check that your token is valid and has the 'repo' scope."
        )
        raise SystemExit(1)
    if response.status_code == 403:
        logger.error(
            "GitHub API returned 403 Forbidden. "
            "Ensure your token has the 'repo' scope."
        )
        raise SystemExit(1)
    response.raise_for_status()
    return response.json()


def _parse_repositories(nodes: list[dict]) -> list[Repository]:
    """Convert raw GraphQL nodes into Repository dataclass instances."""
    repos: list[Repository] = []
    for node in nodes:
        default_branch_ref = node.get("defaultBranchRef") or {}
        repos.append(
            Repository(
                name=node["name"],
                clone_url=node["url"],
                ssh_url=node["sshUrl"],
                is_fork=node["isFork"],
                is_archived=node["isArchived"],
                default_branch=default_branch_ref.get("name", "main"),
            )
        )
    return repos


async def _handle_rate_limit(rate_limit: dict) -> None:
    """Pause and resume automatically if the GitHub API rate limit is nearly exhausted."""
    remaining = rate_limit.get("remaining", _RATE_LIMIT_THRESHOLD + 1)
    if remaining >= _RATE_LIMIT_THRESHOLD:
        return

    reset_at_str: str = rate_limit["resetAt"]
    reset_at = datetime.fromisoformat(reset_at_str.replace("Z", "+00:00"))
    now = datetime.now(tz=timezone.utc)
    wait_seconds = max(0, (reset_at - now).total_seconds()) + _RATE_LIMIT_BUFFER_SECONDS

    minutes, seconds = divmod(int(wait_seconds), 60)
    logger.warning(
        "GitHub API rate limit reached. Resuming in %dm %ds...", minutes, seconds
    )
    await asyncio.sleep(wait_seconds)


async def fetch_org_repos(org: str, token: str) -> list[Repository]:
    """Fetch all repositories for a GitHub organisation using the GraphQL API.

    Uses a paginated query to retrieve up to 100 repositories per request,
    following all pages automatically. Pauses and resumes when the rate limit
    is nearly exhausted. Returns a flat list of Repository instances.
    """
    all_repos: list[Repository] = []
    cursor: str | None = None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        while True:
            data = await with_retry(_fetch_page, client, org, cursor)

            errors = data.get("errors")
            if errors:
                first_error = errors[0]
                error_type = first_error.get("type", "")
                if error_type == "NOT_FOUND":
                    logger.error(
                        "Organisation '%s' not found or is not accessible with the current token.",
                        org,
                    )
                    raise SystemExit(1)
                logger.error("GitHub GraphQL error: %s", first_error.get("message"))
                raise SystemExit(1)

            rate_limit = data.get("data", {}).get("rateLimit", {})
            await _handle_rate_limit(rate_limit)

            org_data = data.get("data", {}).get("organization")
            if org_data is None:
                logger.error(
                    "Organisation '%s' not found or is not accessible with the current token.",
                    org,
                )
                raise SystemExit(1)

            repositories = org_data["repositories"]
            nodes: list[dict] = repositories.get("nodes", [])
            all_repos.extend(_parse_repositories(nodes))

            page_info = repositories["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]

    logger.debug("Fetched %d repositories for organisation '%s'.", len(all_repos), org)
    return all_repos
