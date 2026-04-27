# Research: GitHub Organisation Repository Cloner

**Phase**: 0 — Pre-design research
**Date**: 2026-04-27
**Branch**: `001-github-org-cloner`

---

## Decision 1: GitHub API Protocol — GraphQL vs REST

**Decision**: Use the GitHub GraphQL API (v4) for repository listing.

**Rationale**: A single GraphQL query can fetch up to 100 repositories per
page including all required fields (name, HTTPS URL, SSH URL, fork status,
archived status, default branch) in one network round-trip. The REST endpoint
`GET /orgs/{org}/repos` returns at most 100 repos per page but requires
separate field-level requests and produces more total API traffic. For an org
with 300 repos, GraphQL uses 3 requests vs 3+ REST requests — identical page
count, but GraphQL avoids follow-up requests for additional fields. For rate
limit accounting, GraphQL charges per query complexity (not per request), and
the response always includes the remaining rate limit and reset timestamp,
enabling accurate pause-and-resume logic without an extra API call.

**Alternatives considered**:
- REST (`/orgs/{org}/repos`): Simpler to implement but no native complexity
  budget visibility and requires separate calls for some fields. Rejected
  because spec FR-012 explicitly prefers batch query protocols.
- `gh` CLI (`gh repo list`): Would add a subprocess dependency on `gh` being
  installed, introduces version fragility, and gives no programmatic access to
  rate limit state. Rejected.

---

## Decision 2: Async HTTP Client — httpx vs aiohttp vs urllib

**Decision**: `httpx[asyncio]` pinned at `>=0.27.0`.

**Rationale**: `httpx` supports both synchronous and asynchronous usage from
the same API surface, has first-class Python 3.10+ support, handles HTTP/2,
and is cross-platform (Linux + Windows) without platform-specific event loop
configuration. `aiohttp` is async-only and requires more boilerplate for
session management. The stdlib `urllib` has no native async support and would
require wrapping in `asyncio.to_thread`, adding complexity for no benefit.

**Alternatives considered**:
- `aiohttp`: async-only, slightly more verbose session lifecycle. Rejected in
  favour of `httpx` for its unified sync/async API and simpler usage.
- `urllib` (stdlib): No async support natively. Would require
  `asyncio.to_thread` wrapper, negating the simplicity benefit of stdlib.
  Rejected.
- `requests` (sync only): Incompatible with asyncio. Rejected.

---

## Decision 3: Git Operations — asyncio Subprocesses vs gitpython

**Decision**: `asyncio.create_subprocess_exec` calling the `git` CLI directly.
No `gitpython` or similar library.

**Rationale**: Using `asyncio.create_subprocess_exec` means each git operation
(clone, fetch, pull, status) runs as a non-blocking coroutine, allowing
`asyncio.gather` to run N operations in parallel with a Semaphore cap. This
requires zero additional dependencies (git is assumed to be installed on the
user's machine; it is a prerequisite for a git sync tool). `gitpython` adds a
dependency, has known Windows compatibility rough edges, and wraps subprocess
calls itself without adding meaningful async support.

**Alternatives considered**:
- `gitpython`: Python API for git operations. Adds a dependency, has limited
  async support, and has documented Windows issues with path handling. Rejected.
- `subprocess.run` (sync): Blocks the event loop during each git operation,
  eliminating parallelism. Rejected.
- `pygit2` (libgit2 bindings): Native-speed but requires compiled C extensions,
  adds significant install complexity, and is unnecessary for CLI-level git ops.
  Rejected.

---

## Decision 4: Concurrency Model

**Decision**: `asyncio` throughout, with `asyncio.Semaphore` to bound
concurrent git subprocesses.

**Rationale**: All I/O in this tool is network or subprocess I/O — exactly the
domain where `asyncio` MUST be used per constitution Principle X. The API
fetch phase uses `httpx.AsyncClient`. The git operation phase uses
`asyncio.create_subprocess_exec` wrapped in coroutines and launched via
`asyncio.gather(*tasks)` with a `asyncio.Semaphore(max_concurrent)` guard
(default: 5). This prevents opening 300 git subprocesses simultaneously while
still providing significant parallelism.

**Alternatives considered**:
- `ThreadPoolExecutor`: Would satisfy parallelism but is the "legacy context"
  fallback under Principle X and requires no justification here since asyncio
  is fully applicable. Rejected.
- `ProcessPoolExecutor`: CPU-bound workloads only per Principle X. Git ops are
  I/O-bound. Rejected.

---

## Decision 5: Credential / Token Resolution

**Decision**: Read `GITHUB_TOKEN` environment variable first; fall back to
executing `gh auth token` (if `gh` CLI is present) to retrieve the token from
the `gh` CLI token store. Fail fast with an actionable error if neither yields
a token.

**Rationale**: This covers both CI/CD environments (where `GITHUB_TOKEN` is
the standard) and developer machines (where `gh auth login` is the typical
setup). Neither path hardcodes anything or stores credentials. Aligns with
constitution Principle VII.

**Alternatives considered**:
- OS keychain direct access: Platform-specific APIs (Windows Credential Manager,
  macOS Keychain, libsecret). Too complex, too fragile cross-platform. Rejected.
- `.netrc` file: Would require teaching users to set up `.netrc`. Less common
  for GitHub. Rejected as primary path; still works transparently because `git`
  itself reads `.netrc` during clone/pull.

---

## Decision 6: Clone Protocol Resolution

**Decision**: The GraphQL response includes both `url` (HTTPS) and `sshUrl`
(SSH) for every repository. The tool exposes a `--protocol {https,ssh}`
argument (default: `https`). The user sets it once per machine to match their
credential configuration. No auto-detection.

**Rationale**: Auto-detecting whether SSH keys or HTTPS tokens are configured
is fragile across platforms and environments. Providing an explicit flag is
simpler, testable, and gives the user full control. The default of HTTPS covers
the broadest set of users (works with `GITHUB_TOKEN`/`gh auth`). SSH users set
`--protocol ssh` once.

---

## Decision 7: Retry — Pure asyncio, No Library

**Decision**: Implement `with_retry(coro, max_attempts=3, base_delay=1.0)` in
`retry.py` using `asyncio.sleep` for backoff (1s, 2s, 4s).

**Rationale**: Three retry attempts with exponential backoff catches the vast
majority of transient network failures (DNS blips, brief TCP resets, GitHub
transient 5xx). A pure asyncio implementation requires no additional library.
The `tenacity` library is the common third-party option but is unjustified here
since the custom implementation is 15-20 lines and has no external dependencies.

---

## Decision 8: Dirty Working-Tree Detection

**Decision**: Run `git status --porcelain` in the target repository directory.
If stdout is non-empty, the repo is dirty — skip update, log warning, record
`SKIPPED_DIRTY`.

**Rationale**: `--porcelain` produces machine-readable output: empty string
means clean, any output means dirty. This is cross-platform, works with all
git versions ≥ 1.7, and requires no git library.
