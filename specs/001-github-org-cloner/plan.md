# Implementation Plan: GitHub Organisation Repository Cloner

**Branch**: `001-github-org-cloner` | **Date**: 2026-04-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-github-org-cloner/spec.md`

## Summary

A cross-platform Python CLI tool that lists all repositories in a GitHub
organisation via a single paginated GraphQL query, then clones or updates
each repository in parallel using asyncio subprocesses. Exclusion rules
(prefix, suffix, exact name, glob pattern) are applied before any git
operation. The tool handles rate limiting by pausing with a countdown, retries
failed operations with exponential backoff, skips repositories with
uncommitted local changes, and emits a structured run summary on completion.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: `httpx[asyncio]>=0.27.0` (async GitHub GraphQL
client; justified over stdlib `urllib` because urllib has no native async
support and the tool performs concurrent I/O against the GitHub API)
**Storage**: Local filesystem via `pathlib.Path` — no database
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux + Windows (cross-platform, per constitution)
**Project Type**: CLI tool
**Performance Goals**: Concurrent clone/update of N repos using
`asyncio.gather` with a bounded semaphore (default concurrency: 5 parallel
git operations); GraphQL batch listing minimises total API calls to
`ceil(N/100)` requests for N repositories
**Constraints**: No hardcoded credentials; cross-platform paths via
`pathlib.Path`; all public functions typed and docstring-annotated; no
`print()` outside of REPL helpers; third-party packages pinned in
`github/requirements.txt`
**Scale/Scope**: Single org per invocation; handles 100+ repositories;
automatic pagination; automatic rate-limit pause-and-resume

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Language & Runtime | ✅ PASS | Python 3.10+; no shell core logic; cross-platform |
| II. Architecture & Module Isolation | ✅ PASS | All code in `github/` domain; no cross-domain imports; `lib/` not needed (only one domain) |
| III. Code Standards | ✅ PASS | Docstrings on all public symbols; no inline comments; type hints mandatory; `logging` only |
| IV. CLI Design | ✅ PASS | `argparse`; `--help`; `--verbose`; exit 0/non-zero; `pathlib.Path` for all path args |
| V. Idempotency | ✅ PASS | Clone-if-missing + update-if-exists = same end state on every run; no destructive ops |
| VI. Dependency Management | ✅ PASS | Only `httpx` (justified); pinned in `github/requirements.txt`; no root-level file |
| VII. Authentication & Secrets | ✅ PASS | Reads `GITHUB_TOKEN` env var or `gh` CLI token store; fails fast with actionable error if absent |
| VIII. Documentation | ✅ PASS | `github/README.md` required; root `README.md` index entry required |
| IX. Testing | ✅ PASS | Business logic separated from CLI entry point; tests in `tests/github/` |
| X. Concurrency & Parallelism | ✅ PASS | `asyncio` for API + git ops; `asyncio.gather` + `Semaphore` for bounded parallel git subprocesses |

**All gates pass. No complexity violations to justify.**

## Project Structure

### Documentation (this feature)

```text
specs/001-github-org-cloner/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── cli-contract.md
│   └── graphql-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
github/
├── __init__.py
├── org_cloner.py        # CLI entry point: argparse, version guard, main()
├── cloner.py            # Core business logic: sync_organisation(), clone_repo(), update_repo()
├── github_client.py     # Async GraphQL client: fetch_org_repos(), resolve_token()
├── exclusion.py         # Exclusion rule matching: matches_any(), build_rules()
├── models.py            # Dataclasses + Enums: Repository, ExclusionRule, SyncResult, RunSummary
├── retry.py             # Exponential backoff: with_retry()
├── requirements.txt     # httpx[asyncio]>=0.27.0
└── README.md

tests/
└── github/
    ├── __init__.py
    ├── test_exclusion.py       # Unit: all four rule types + combinations
    ├── test_models.py          # Unit: RunSummary aggregation, Outcome enum
    ├── test_retry.py           # Unit: backoff timing, retry count, eventual success
    ├── test_cloner.py          # Unit: sync logic with mocked git subprocess
    └── test_github_client.py   # Unit: GraphQL pagination, rate-limit parsing, token resolution
```

**Structure Decision**: Single-project layout under `github/` domain per
constitution Principle II. No cross-domain imports. Tests mirror the domain
structure at `tests/github/`. All path operations use `pathlib.Path`.
