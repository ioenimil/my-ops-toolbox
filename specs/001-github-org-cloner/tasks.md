---

description: "Task list for github-org-cloner implementation"
---

# Tasks: GitHub Organisation Repository Cloner

**Input**: Design documents from `specs/001-github-org-cloner/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅

**Tests**: Included in Final Phase — mandated by constitution Principle IX. Not TDD
(TDD not explicitly requested); tests are written after implementation.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every task description

## Path Conventions

- Domain module: `github/`
- Tests: `tests/github/`
- Design docs: `specs/001-github-org-cloner/`

---

## Phase 1: Setup

**Purpose**: Create the project skeleton — all package files as stubs so later
tasks can be developed independently and in parallel.

- [x] T001 Create github/ package skeleton — create `github/__init__.py`,
  `github/org_cloner.py`, `github/cloner.py`, `github/github_client.py`,
  `github/exclusion.py`, `github/models.py`, `github/retry.py` each as empty
  Python files with module-level docstrings only
- [x] T002 [P] Create `github/requirements.txt` — single entry:
  `httpx[asyncio]>=0.27.0`
- [x] T003 [P] Create tests/github/ package skeleton — create
  `tests/__init__.py`, `tests/github/__init__.py`,
  `tests/github/test_models.py`, `tests/github/test_retry.py`,
  `tests/github/test_exclusion.py`, `tests/github/test_cloner.py`,
  `tests/github/test_github_client.py` each as empty files with a single
  placeholder docstring

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story
can be implemented. All user story tasks depend on this phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Implement all dataclasses and enums in `github/models.py` —
  `Organisation(name: str)`, `Repository(name, clone_url, ssh_url, is_fork,
  is_archived, default_branch)`, `Outcome` enum with members CLONED / UPDATED /
  UP_TO_DATE / SKIPPED_EXCLUDED / SKIPPED_DIRTY / FAILED, `SyncResult(repo_name:
  str, outcome: Outcome, error: str | None)`, `RunSummary` dataclass with fields
  cloned / updated / up_to_date / skipped_excluded / skipped_dirty / failed /
  total; all fields typed; all classes have docstrings; use `@dataclass(frozen=True)`
  where mutable state is not required
- [x] T005 [P] Implement `github/retry.py` — single public coroutine
  `with_retry(coro_fn: Callable, *args, max_attempts: int = 3,
  base_delay: float = 1.0, **kwargs) -> Any`; retries on any `Exception`;
  backoff delays: 1 s, 2 s, 4 s (base_delay * 2^attempt); logs each retry at
  WARNING level with attempt number and error; re-raises on final attempt
- [x] T006 Implement `resolve_token()` in `github/github_client.py` —
  signature `resolve_token() -> str`; read `os.environ.get("GITHUB_TOKEN")`
  first; if absent, run `subprocess.run(["gh", "auth", "token"], ...)` and
  capture stdout; if both fail: call `logging.error(...)` with an actionable
  message instructing the user to set `GITHUB_TOKEN` or run `gh auth login`,
  then `raise SystemExit(1)`; function has a docstring; no credentials logged
- [x] T007 Implement `fetch_org_repos()` in `github/github_client.py` —
  signature `async def fetch_org_repos(org: str, token: str) ->
  list[Repository]`; use `httpx.AsyncClient` with `Authorization: Bearer
  <token>` header against `https://api.github.com/graphql`; send the
  paginated GraphQL query from `contracts/graphql-contract.md`; loop until
  `pageInfo.hasNextPage` is False; after each page check `rateLimit.remaining`;
  if remaining < 50 compute wait seconds from `rateLimit.resetAt`, log
  `"GitHub API rate limit reached. Resuming in Xm Ys..."`, then
  `await asyncio.sleep(wait_seconds + 5)`; handle 401/403/404 by logging an
  actionable error and raising `SystemExit(1)`; wrap transient 5xx responses
  with `with_retry`; return `list[Repository]` with all pages combined
- [x] T008 Implement argument parser and version guard in `github/org_cloner.py`
  — at module level check `sys.version_info >= (3, 10)` and raise `SystemExit`
  with a clear message if not; implement `build_parser() -> argparse.ArgumentParser`
  returning a parser with: `ORG` positional str, `-o/--output-dir` as
  `pathlib.Path` (default computed at runtime as `Path.cwd() / ORG`),
  `--exclude-prefix` (append action, dest `exclude_prefixes`),
  `--exclude-suffix` (append action, dest `exclude_suffixes`),
  `--exclude` (append action, dest `exclude_names`),
  `--exclude-pattern` (append action, dest `exclude_patterns`),
  `--protocol` choice of `{https, ssh}` defaulting to `https`,
  `--max-concurrent` int defaulting to 5 validated in range 1–50,
  `--verbose` store_true; all arguments have help strings
- [x] T009 Implement `run_git_command()` in `github/cloner.py` — signature
  `async def run_git_command(cmd: list[str], cwd: Path) ->
  tuple[int, str, str]`; use `asyncio.create_subprocess_exec(*cmd, cwd=cwd,
  stdout=PIPE, stderr=PIPE)`; await communicate(); decode stdout/stderr as UTF-8;
  log stderr at DEBUG level; return `(returncode, stdout, stderr)`

**Checkpoint**: Foundation ready — all user story phases can now begin.

---

## Phase 3: User Story 1 - Initial Organisation Sync (Priority: P1) 🎯 MVP

**Goal**: Clone all accessible repositories of a GitHub organisation into a
local target directory in a single command invocation.

**Independent Test**: With an empty target directory, run the tool against an
org with ≥ 3 repositories. Every repository must appear as a local directory.
The summary must report the correct clone count.

### Implementation for User Story 1

- [x] T010 [P] [US1] Implement `is_valid_git_repo(path: Path) -> bool` in
  `github/cloner.py` — runs `run_git_command(["git", "rev-parse",
  "--git-dir"], cwd=path)`; returns `True` if returncode is 0; returns `False`
  otherwise (directory exists but is not a git repo)
- [x] T011 [P] [US1] Implement `clone_repo(repo: Repository, target_dir:
  Path, protocol: str, semaphore: asyncio.Semaphore) -> SyncResult` in
  `github/cloner.py` — acquire semaphore before git operation; select
  `repo.clone_url` if protocol == "https" else `repo.ssh_url`; run
  `run_git_command(["git", "clone", url, str(target_dir / repo.name)], cwd=target_dir)`
  wrapped in `with_retry`; return `SyncResult(repo.name, Outcome.CLONED, None)`
  on success or `SyncResult(repo.name, Outcome.FAILED, error_message)` on
  exhausted retries; log each outcome at INFO (verbose) or DEBUG level
- [x] T012 [US1] Implement `sync_organisation()` clone-only path in
  `github/cloner.py` — signature `async def sync_organisation(org: str,
  target_dir: Path, token: str, rules: list = [], protocol: str = "https",
  max_concurrent: int = 5) -> list[SyncResult]`; resolve token; create
  `target_dir` if absent via `target_dir.mkdir(parents=True, exist_ok=True)`;
  fetch repos via `fetch_org_repos()`; for each repo whose
  `target_dir / repo.name` does not exist: schedule `clone_repo` via
  `asyncio.gather` bounded by `asyncio.Semaphore(max_concurrent)`; collect
  and return all `SyncResult` objects
- [x] T013 [US1] Implement `build_summary(results: list[SyncResult]) ->
  RunSummary` and `format_summary(summary: RunSummary) -> str` in
  `github/cloner.py` — `build_summary` counts each `Outcome` member and
  returns a `RunSummary`; `format_summary` returns the summary table string
  matching the output format in `contracts/cli-contract.md`; both functions
  use `logging` only (no `print`)
- [x] T014 [US1] Implement `main()` in `github/org_cloner.py` — parse args
  via `build_parser().parse_args()`; configure logging (DEBUG if `--verbose`,
  else WARNING); call `resolve_token()`; resolve `output_dir` as
  `pathlib.Path`; call `asyncio.run(sync_organisation(...))`; call
  `build_summary()` and `format_summary()` and output summary via logging;
  exit with `sys.exit(1)` if `summary.failed > 0`, else `sys.exit(0)`

**Checkpoint**: US1 fully functional — run `python -m github.org_cloner <org>`
and verify all repositories are cloned with a correct summary.

---

## Phase 4: User Story 2 - Incremental Update of Existing Clones (Priority: P1)

**Goal**: Re-running the tool updates existing local repositories without
re-cloning; new repositories are cloned fresh; unchanged repos report
up-to-date.

**Independent Test**: After a full sync, push a new commit to one repository
and add a new one. Re-run the tool. Verify the updated repo reflects the new
commit, the new repo is cloned, and unchanged repos are reported as up-to-date
without re-downloading data.

### Implementation for User Story 2

- [x] T015 [P] [US2] Implement `is_dirty(repo_dir: Path) -> bool` in
  `github/cloner.py` — run `run_git_command(["git", "status", "--porcelain"],
  cwd=repo_dir)`; return `True` if stdout is non-empty; return `False` if
  stdout is empty (clean working tree)
- [x] T016 [US2] Implement `update_repo(repo: Repository, repo_dir: Path,
  semaphore: asyncio.Semaphore) -> SyncResult` in `github/cloner.py` —
  acquire semaphore; call `is_dirty(repo_dir)`; if dirty: log a WARNING
  including `repo.name`, return `SyncResult(repo.name, Outcome.SKIPPED_DIRTY,
  None)`; capture HEAD ref before update via `run_git_command(["git", "rev-parse",
  "HEAD"], ...)`; run `git fetch --prune` then `git pull --ff-only` wrapped in
  `with_retry`; capture HEAD ref after update; if refs differ return
  `SyncResult(repo.name, Outcome.UPDATED, None)`; if refs equal return
  `SyncResult(repo.name, Outcome.UP_TO_DATE, None)`; on exhausted retries
  return `SyncResult(repo.name, Outcome.FAILED, error_message)`
- [x] T017 [US2] Extend `sync_organisation()` in `github/cloner.py` to handle
  the update path — for each repo where `target_dir / repo.name` already
  exists: call `is_valid_git_repo()`; if not valid: log a WARNING naming the
  conflicting directory, append `SyncResult(repo.name, Outcome.SKIPPED_DIRTY,
  "directory exists but is not a git repository")`; if valid: schedule
  `update_repo` via `asyncio.gather` with the shared Semaphore; combine clone
  results (new repos) and update results (existing repos) into a single
  returned `list[SyncResult]`

**Checkpoint**: US2 fully functional — re-running the tool completes without
re-cloning and reports each repo's outcome accurately.

---

## Phase 5: User Story 3 - Selective Exclusion by Name Pattern (Priority: P2)

**Goal**: Repositories matching any active exclusion rule (prefix, suffix,
exact name, glob pattern) are skipped entirely and reported as excluded.

**Independent Test**: Run the tool with a prefix exclusion that matches a known
subset of the org's repositories. Verify none of the matching repos are
cloned or modified. Verify the summary reports the excluded count.

### Implementation for User Story 3

- [x] T018 [P] [US3] Add ExclusionRule concrete types to `github/models.py` —
  add `@dataclass(frozen=True)` classes `PrefixRule(prefix: str)`,
  `SuffixRule(suffix: str)`, `ExactRule(value: str)`, `GlobRule(pattern: str)`;
  each MUST implement `matches(self, name: str) -> bool`; `PrefixRule.matches`
  uses `str.startswith`; `SuffixRule.matches` uses `str.endswith`;
  `ExactRule.matches` uses `==`; `GlobRule.matches` uses
  `fnmatch.fnmatch(name, self.pattern)`; define `ExclusionRule` as
  `Union[PrefixRule, SuffixRule, ExactRule, GlobRule]` type alias; all classes
  have docstrings
- [x] T019 [P] [US3] Implement `build_rules()` and `matches_any()` in
  `github/exclusion.py` — `build_rules(prefixes: list[str] | None, suffixes:
  list[str] | None, names: list[str] | None, patterns: list[str] | None) ->
  list[ExclusionRule]` constructs the appropriate rule type for each non-empty
  list entry; `matches_any(repo_name: str, rules: list[ExclusionRule]) -> bool`
  returns `True` if any rule's `matches()` returns `True`; both functions
  have docstrings and type hints
- [x] T020 [US3] Integrate exclusion into `sync_organisation()` in
  `github/cloner.py` — before any git operation, call `matches_any(repo.name,
  rules)`; if True: append `SyncResult(repo.name, Outcome.SKIPPED_EXCLUDED,
  None)` and continue to next repo; excluded repos MUST NOT be cloned, updated,
  or touched in any way; log each exclusion at DEBUG level when `--verbose`
- [x] T021 [US3] Wire exclusion arguments into `main()` in
  `github/org_cloner.py` — after parsing args, call `build_rules(
  args.exclude_prefixes, args.exclude_suffixes, args.exclude_names,
  args.exclude_patterns)`; pass the resulting `list[ExclusionRule]` as the
  `rules` argument to `sync_organisation()`

**Checkpoint**: US3 fully functional — exclusion rules of all four types
applied; excluded repos absent from output; summary shows correct skipped count.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Tests (mandated by constitution Principle IX), documentation,
and validation.

- [x] T022 [P] Write `tests/github/test_models.py` — unit tests for:
  `Outcome` enum has all 6 members; `SyncResult` stores outcome and error
  correctly; `RunSummary` total equals sum of all counts; `RunSummary` built
  from known results produces correct per-outcome counts
- [x] T023 [P] Write `tests/github/test_retry.py` — unit tests for
  `with_retry`: coroutine succeeds on first attempt (no retries); coroutine
  fails once then succeeds (1 retry); coroutine fails 3 times then raises
  on final attempt; verify asyncio.sleep is called with correct backoff
  durations (mock asyncio.sleep)
- [x] T024 [P] Write `tests/github/test_exclusion.py` — unit tests for all
  four ExclusionRule subtypes: `PrefixRule("arch-").matches("arch-foo")` True,
  `matches("foo")` False; analogous cases for SuffixRule, ExactRule; GlobRule
  with `*` and `?` wildcards; `matches_any` returns True when any rule matches;
  returns False when no rules match; empty rules list always returns False;
  `build_rules` produces correct rule types from input lists
- [x] T025 [P] Write `tests/github/test_cloner.py` — unit tests for:
  `is_valid_git_repo` returns True when git rev-parse exits 0, False otherwise;
  `is_dirty` returns True when git status --porcelain has output, False when
  empty; `build_summary` produces correct RunSummary counts from a known
  list of SyncResults; use `unittest.mock.AsyncMock` to mock
  `run_git_command` responses
- [x] T026 [P] Write `tests/github/test_github_client.py` — unit tests for:
  `resolve_token` returns GITHUB_TOKEN when env var is set; calls gh fallback
  when GITHUB_TOKEN absent; raises SystemExit when both absent; pagination
  loop fetches all pages (mock two-page response); rate-limit pause triggered
  when remaining < 50 (mock asyncio.sleep); 401 response raises SystemExit;
  use `unittest.mock.patch` and `respx` or `httpx` mock transport
- [x] T027 Write `github/README.md` — sections: Purpose, Prerequisites
  (Python 3.10+, git, GitHub token via GITHUB_TOKEN or gh auth login), Usage
  Examples (initial sync, incremental update, exclusion rules, SSH protocol,
  verbose mode, custom output directory), Troubleshooting (missing token,
  dirty repo warning, rate limit pause)
- [x] T028 Add `github-org-cloner` entry to root `README.md` — one-line
  description in the domains index table under the `github/` domain row;
  create the table if it does not exist
- [ ] T029 Run quickstart validation — follow each checklist item in
  `specs/001-github-org-cloner/quickstart.md`; verify `--help` exits 0;
  sync a real org and confirm repository directories; re-run and confirm
  idempotency; apply an exclusion rule and confirm excluded repos absent;
  introduce uncommitted changes to a local repo and confirm `skipped (dirty)`;
  unset GITHUB_TOKEN and confirm actionable error message on stderr

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational — no dependencies on US2 or US3
- **US2 (Phase 4)**: Depends on Foundational + US1 (extends sync_organisation)
- **US3 (Phase 5)**: Depends on Foundational; independent of US2 but integrates with sync_organisation from US1
- **Polish (Final)**: Depends on all user story phases being complete

### User Story Dependencies

- **US1 (P1)**: Can start immediately after Foundational — no story dependencies
- **US2 (P1)**: Extends `sync_organisation()` built in US1 — must follow US1
- **US3 (P2)**: Adds exclusion layer to `sync_organisation()` — should follow US1; independent of US2

### Within Each User Story

- T010, T011 [P] can run in parallel (independent functions in cloner.py)
- T012 depends on T010 + T011 (calls both)
- T013 can run in parallel with T010/T011
- T014 depends on T012 + T013
- T015 is independent within US2 phase ([P])
- T016 depends on T015
- T017 depends on T016
- T018, T019 [P] can run in parallel within US3
- T020 depends on T018 + T019
- T021 depends on T020
- All Polish tasks T022–T026 [P] can run in parallel once implementation is complete

### Parallel Opportunities

```bash
# Phase 1: all in parallel
T001, T002, T003

# Phase 2: T004 first, then T005–T009 in parallel
T004
T005, T006  # T005 independent; T006 independent of T005
# T007 depends on T006 (calls resolve_token)
T007, T008, T009  # T007 after T006; T008 and T009 independent of each other

# Phase 3: T010, T011, T013 in parallel; T012 after T010+T011; T014 last
T010, T011, T013
T012        # after T010 + T011
T014        # after T012 + T013

# Phase 4: T015 first; T016 after T015; T017 after T016
T015
T016
T017

# Phase 5: T018 + T019 in parallel; T020 after both; T021 after T020
T018, T019
T020
T021

# Final Phase: T022–T026 all in parallel; T027–T029 sequentially
T022, T023, T024, T025, T026
T027, T028
T029
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (T010–T014)
4. **STOP and VALIDATE**: run `python -m github.org_cloner <org>` against a
   real organisation; confirm cloning works end-to-end
5. Demo / use — the tool is already useful at this point

### Incremental Delivery

1. Setup + Foundational → infrastructure ready
2. US1 → clone all repos (MVP, demo-ready)
3. US2 → add incremental update (safe to re-run daily)
4. US3 → add exclusion rules (full feature)
5. Polish → tests, docs, validation

---

## Notes

- `[P]` tasks operate on different files or independent functions — safe to
  run in parallel
- `[Story]` label maps each task to a user story for traceability
- `asyncio.Semaphore(max_concurrent)` is shared across clone + update
  coroutines in `sync_organisation()` — do not create a new semaphore per repo
- Verify each user story checkpoint independently before moving to the next story
- All path arguments MUST use `pathlib.Path` — never raw `str` for file paths
- `print()` is forbidden everywhere — use `logging` exclusively
