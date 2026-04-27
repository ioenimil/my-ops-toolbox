# Feature Specification: GitHub Organisation Repository Cloner

**Feature Branch**: `001-github-org-cloner`
**Created**: 2026-04-27
**Status**: Draft
**Input**: User description: "A command-line tool that synchronises all repositories belonging to a GitHub organisation onto a local machine, with support for re-running to stay up to date and for excluding repositories by prefix, suffix, pattern, or exact name."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initial Organisation Sync (Priority: P1)

A user needs all repositories of a GitHub organisation on their local machine.
They run the tool once, providing the organisation name. Every accessible
repository is cloned into a dedicated subdirectory inside a target directory.
Upon completion the user sees a summary showing how many repositories were
cloned and how many (if any) were skipped.

**Why this priority**: This is the core value of the tool — without it nothing
else works.

**Independent Test**: Run the tool against an organisation with at least three
repositories that do not yet exist locally. Verify each repository is present
as a directory and is a valid local repository. Verify the summary reports the
correct clone count.

**Acceptance Scenarios**:

1. **Given** a GitHub organisation with N accessible repositories and an empty
   target directory, **When** the user runs the tool with the organisation name,
   **Then** N subdirectories are created, one per repository, each containing a
   complete local copy of that repository.
2. **Given** a GitHub organisation the user cannot access, **When** the user
   runs the tool, **Then** the tool exits with a non-zero code and displays a
   clear, human-readable error explaining the access problem.
3. **Given** an organisation with zero repositories, **When** the user runs the
   tool, **Then** it exits successfully with a summary reporting zero clones.

---

### User Story 2 - Incremental Update of Existing Clones (Priority: P1)

A user who previously synced an organisation runs the tool again to stay up to
date. Repositories already present locally are brought to the latest state
from the remote. Repositories added to the organisation since the last run are
cloned fresh. No unnecessary data transfer occurs for repositories that are
already current.

**Why this priority**: Without idempotent update behaviour the tool is only
useful once — re-running must be safe and efficient for the tool to be
trustworthy in daily workflows.

**Independent Test**: Sync an organisation, then push a new commit to one
repository and add a new repository to the organisation. Re-run the tool.
Verify the existing repository reflects the new commit, the new repository is
cloned, and previously cloned unmodified repositories are reported as
already-up-to-date without re-downloading data.

**Acceptance Scenarios**:

1. **Given** an organisation previously synced and one of its repositories has
   received new commits since the last run, **When** the user re-runs the tool,
   **Then** the local copy of that repository reflects the latest commits.
2. **Given** an organisation previously synced and a new repository has been
   added since the last run, **When** the user re-runs the tool, **Then** the
   new repository is cloned into the target directory.
3. **Given** an organisation where no repositories have changed since the last
   sync, **When** the user re-runs the tool, **Then** it completes without
   re-downloading repository data and the summary reports all repositories as
   already up to date.

---

### User Story 3 - Selective Exclusion by Name Pattern (Priority: P2)

A user wants to sync an organisation but deliberately skip certain repositories.
They provide one or more exclusion rules — by prefix, by suffix, by exact name,
or by a substring or wildcard pattern — as arguments to the tool. Only
repositories whose names do not match any exclusion rule are cloned or updated.
Excluded repositories are listed in the run summary.

**Why this priority**: Organisations often contain archived, deprecated, or
irrelevant repositories. Blanket cloning without filtering wastes disk space
and time.

**Independent Test**: Run the tool with an exclusion rule that matches a known
subset of the organisation's repositories. Verify none of the matching
repositories are cloned or modified. Verify the summary reports the excluded
count.

**Acceptance Scenarios**:

1. **Given** an organisation containing repos `archive-alpha`, `archive-beta`,
   and `core-service`, **When** the user runs the tool with a prefix exclusion
   of `archive-`, **Then** only `core-service` is cloned or updated and both
   archive repos are reported as skipped.
2. **Given** an organisation containing repos `service-v1`, `service-v2`, and
   `service-deprecated`, **When** the user runs the tool with a suffix exclusion
   of `-deprecated`, **Then** only `service-v1` and `service-v2` are processed.
3. **Given** an organisation containing a repo named `internal-sandbox`,
   **When** the user runs the tool with an exact-name exclusion of
   `internal-sandbox`, **Then** that repository is never cloned or touched.
4. **Given** an organisation where the user supplies a wildcard pattern such as
   `test-*`, **When** the tool runs, **Then** all repositories whose names match
   the pattern are skipped.
5. **Given** multiple exclusion rules of different types provided together,
   **When** the tool runs, **Then** any repository matching at least one rule
   is excluded.

---

### Edge Cases

- What happens if the target directory contains a subdirectory with the same
  name as a repository but that subdirectory is not a valid local repository?
  The tool MUST warn the user and skip that entry rather than overwriting it.
- What if one repository update fails mid-run (e.g., network timeout)?
  The tool MUST retry that repository up to 3 times with exponential backoff.
  If all retries fail, the tool MUST continue processing remaining repositories,
  report all ultimately failed repositories in the final summary, and exit with
  a non-zero code.
- What if the organisation has hundreds of repositories split across multiple
  pages of API results? The tool MUST retrieve and process all pages
  automatically using batch queries where available; the user MUST NOT need
  to paginate manually.
- What if the GitHub API rate limit is exhausted mid-run? The tool MUST pause,
  display the time remaining until the rate limit resets, and resume
  automatically — it MUST NOT fail or require a manual re-run.
- What if the user has no system-level credentials configured?
  The tool MUST fail immediately with an actionable message explaining how to
  configure credentials.
- What if a local repository already has uncommitted changes (staged or
  unstaged) when the tool attempts to update it? The tool MUST skip the
  update for that repository, log a warning identifying it by name, continue
  processing all other repositories, and report it in the summary as
  "skipped (dirty)". The tool MUST NOT modify the working tree of a
  repository that has uncommitted changes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST accept a GitHub organisation name as a required
  argument.
- **FR-002**: The tool MUST accept an optional target directory argument. If
  omitted, it MUST default to a subdirectory named after the organisation
  within the current working directory.
- **FR-003**: The tool MUST clone every accessible repository of the specified
  organisation that is not excluded by any active exclusion rule.
- **FR-004**: The tool MUST update repositories that already exist locally to
  reflect the latest remote state without re-cloning from scratch.
- **FR-005**: The tool MUST support excluding repositories whose names begin
  with a specified prefix (e.g., `archive-`).
- **FR-006**: The tool MUST support excluding repositories whose names end with
  a specified suffix (e.g., `-deprecated`).
- **FR-007**: The tool MUST support excluding repositories by their exact,
  full name.
- **FR-008**: The tool MUST support excluding repositories whose names match a
  wildcard pattern (e.g., `test-*`, `*-v1`).
- **FR-009**: Multiple exclusion rules of any combination of types MUST be
  accepted simultaneously; a repository matching any one rule is excluded.
- **FR-010**: The tool MUST authenticate using credentials already stored on
  the user's system and MUST NOT prompt for or store credentials itself. The
  tool MUST NOT enforce a specific clone protocol (HTTPS or SSH); it MUST
  use whichever clone URL the system's default credential configuration
  resolves to, allowing each machine to honour its own setup.
- **FR-011**: The tool MUST fail immediately with a clear, actionable error
  message if system-level credentials are absent or insufficient.
- **FR-012**: The tool MUST retrieve repository listings using the most
  efficient available query protocol, preferring batch queries (e.g., a
  single paginated GraphQL query) over multiple individual REST calls, in
  order to minimise the total number of API requests. It MUST automatically
  retrieve all pages without user intervention.
- **FR-017**: The tool MUST detect when the GitHub API rate limit is
  exhausted mid-run, pause with a visible message showing the time remaining
  until the limit resets, and automatically resume once the limit resets —
  requiring no user interaction.
- **FR-013**: The tool MUST warn and skip (not overwrite) a local directory
  that shares a repository's name but is not a valid local repository.
- **FR-014**: If a clone or update operation fails, the tool MUST retry that
  operation up to 3 times using exponential backoff before marking the
  repository as failed. After exhausting retries, the tool MUST continue
  processing remaining repositories and MUST report all ultimately failed
  repositories in the final summary.
- **FR-015**: The tool MUST display a completion summary reporting counts of
  repositories cloned, updated, skipped (excluded), skipped (dirty), already
  up to date, and failed. This summary MUST appear after every run regardless
  of verbosity level.
- **FR-019**: In default mode the tool MUST produce no per-repository output
  during the run, emitting only the final summary. When run with the verbose
  flag, the tool MUST stream the outcome of each repository (name and result)
  to output as it is processed, in addition to the final summary.
- **FR-016**: The tool MUST exit with code 0 when all processed repositories
  succeed and with a non-zero code if any repository operation fails or if
  a fatal error occurs.
- **FR-018**: The tool MUST detect uncommitted changes (staged or unstaged) in
  a local repository before attempting to update it. If uncommitted changes
  are present, the tool MUST skip the update, emit a named warning, continue
  with all other repositories, and record the repository as "skipped (dirty)"
  in the run summary. The tool MUST NOT modify the working tree of any
  repository that has uncommitted changes.

### Key Entities

- **Organisation**: A GitHub organisation identified by its unique name.
  Owns a collection of repositories.
- **Repository**: A single version-controlled project belonging to the
  organisation, identified by its name and remote URL.
- **ExclusionRule**: A filter applied to repository names. Types: prefix,
  suffix, exact name, wildcard pattern. A repository matching any rule is
  excluded from all operations.
- **SyncResult**: The outcome of a single repository operation — one of:
  cloned, updated, already-up-to-date, skipped (excluded), skipped (dirty),
  or failed.
- **RunSummary**: Aggregated counts of all SyncResults for a single tool
  invocation, displayed to the user on completion.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can sync all repositories of an organisation with a single
  command — no manual iteration or scripting required.
- **SC-002**: Re-running the tool against a previously synced organisation where
  nothing has changed completes without re-downloading any repository data.
- **SC-003**: Every repository matching an active exclusion rule is absent from
  the target directory after the tool completes (never cloned) or untouched
  (if previously cloned before the rule was added).
- **SC-004**: When credentials are absent or invalid, the tool surfaces a
  human-readable message that tells the user exactly what to do to resolve the
  issue, within the first few lines of output.
- **SC-005**: The completion summary accurately reports the count of
  repositories in each outcome category (cloned, updated, up-to-date, skipped,
  failed) after every run.
- **SC-006**: The tool successfully completes a sync for an organisation with
  100+ repositories without requiring any user interaction beyond the initial
  command.

## Assumptions

- The user has valid GitHub credentials configured at the system level (e.g.,
  via an authenticated CLI tool or environment variable) before running the
  tool for the first time. The tool does not enforce HTTPS or SSH; it honours
  whichever protocol the system resolves, so different machines may use
  different protocols transparently.
- Both public and private repositories accessible to the authenticated user are
  included by default; visibility is controlled by the user's credential scope.
- Fork repositories belonging to the organisation are included by default;
  users may exclude them using pattern-based exclusion rules if desired.
- The default target directory is a new subdirectory named after the
  organisation, created inside the current working directory if no target is
  specified.
- Wildcard pattern exclusion supports `*` as a zero-or-more-character wildcard
  and `?` as a single-character wildcard, consistent with common shell glob
  conventions.
- Archived repositories are treated the same as active ones unless explicitly
  excluded by the user.
- The tool operates on the default branch of each repository; no multi-branch
  synchronisation is in scope for this version.

## Clarifications

### Session 2026-04-27

- Q: What should the tool do when the GitHub API rate limit is exhausted during a sync? → A: Pause automatically with a visible countdown to the reset time and resume once the limit resets; additionally, prefer batch/GraphQL queries over multiple individual REST calls to minimise total API call volume.
- Q: What should the tool do if a local repository has uncommitted changes when an update is attempted? → A: Skip the update, emit a named warning, continue with all other repositories, and report the repository as "skipped (dirty)" in the summary. Never modify the working tree of a dirty repository.
- Q: Which clone protocol (HTTPS or SSH) should the tool use? → A: No protocol enforced — honour whichever clone URL the system's credential configuration resolves to; different machines may use different protocols transparently.
- Q: Should the tool show per-repository status in real time or only a final summary? → A: Summary-only by default; verbose flag streams each repository's outcome live as it is processed, in addition to the final summary.
- Q: Should the tool automatically retry a failed clone or update operation before marking it as failed? → A: Yes — retry up to 3 times with exponential backoff; only mark as failed after all retries are exhausted.
