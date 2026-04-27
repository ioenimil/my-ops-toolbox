<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Bump type: MINOR (new principle added)

Principles added:
  X. Concurrency & Parallelism

Principles modified: None
Principles removed: None

Sections modified:
  - Quality & Compliance: added concurrency violation to the merge-block checklist

Templates reviewed:
  - .specify/templates/plan-template.md    ✅ (Constitution Check gate aligns; no update needed)
  - .specify/templates/spec-template.md   ✅ (no concurrency-specific sections required)
  - .specify/templates/tasks-template.md  ✅ (aligns; parallelism noted in [P] task convention)
  - .specify/templates/commands/          ✅ (no command files present; N/A)

Deferred TODOs: None
-->

# my-ops-toolbox Constitution

## Core Principles

### I. Language & Runtime

The primary language is Python 3.10+. No script may target a Python version below 3.10.
Shell scripts are permitted only as thin wrappers or bootstrap helpers and MUST NOT contain
core logic. All tools MUST operate correctly on both Linux and Windows without
platform-specific branching embedded in core logic.

### II. Architecture & Module Isolation

Tools are organised by domain into subdirectories (e.g., `github/`, `infra/`, `vscode/`).
Each subdirectory is a self-contained module: it owns its own dependencies, README, and
entry points. Cross-domain imports between subdirectories are forbidden. Shared utilities
MUST live in a top-level `lib/` directory and MUST only be placed there when used by two
or more domains.

### III. Code Standards

All public functions, classes, and modules MUST have docstrings. Inline comments are
forbidden; if logic requires explanation, it MUST be refactored into a named function
with a docstring. Type hints are mandatory on all function signatures. The `logging`
module is the only permitted output mechanism — `print()` is forbidden except in
interactive REPL helpers.

### IV. CLI Design

Every executable script MUST expose a full `argparse` CLI with `--help` support, sensible
defaults, and a `--verbose` flag that enables DEBUG-level logging. Scripts MUST exit with
code `0` on success and a non-zero code on failure. All path arguments MUST be handled via
`pathlib.Path` and resolve correctly on both Linux and Windows.

### V. Idempotency

Every script MUST be safe to run multiple times against the same target and produce the
same end state. Destructive operations (delete, overwrite, replace) MUST be gated behind
explicit flags and MUST log what they are about to do before executing the action.

### VI. Dependency Management

Third-party packages MUST be justified against the standard library alternative. The Python
standard library is always preferred. When a third-party package is required, it MUST be
pinned in a `requirements.txt` local to that domain subdirectory. A root-level
`requirements.txt` is forbidden.

### VII. Authentication & Secrets

No credentials, tokens, or secrets may be hardcoded or committed to the repository. All
credential resolution MUST delegate to an existing system-level store (e.g., the `gh` CLI
token store, SSH agent, or OS keychain) and MUST fail fast with an actionable error
message if credentials are unavailable.

### VIII. Documentation

Every domain subdirectory MUST contain a `README.md` documenting purpose, prerequisites,
and usage examples for each script it contains. The repository root `README.md` MUST
provide an index of all domains with one-line descriptions.

### IX. Testing

Business logic MUST be extracted into testable functions, separate from CLI entry points.
Tests MUST live in a `tests/` directory mirroring the domain structure (e.g.,
`tests/github/`, `tests/infra/`). Scripts with no testable logic are exempt from test
coverage requirements, but the separation between business logic and CLI entry points MUST
still be maintained.

### X. Concurrency & Parallelism

Where multiple independent operations exist, parallelism MUST be used — sequential
execution of inherently parallelisable workloads is a code-quality violation.

- **I/O-bound work** (network calls, file reads across independent targets, subprocess
  spawning): `asyncio` MUST be used. `asyncio` is the default concurrency primitive for
  all new scripts that perform I/O on more than one target.
- **CPU-bound work** (data transformation, compression, hashing across independent
  inputs): `concurrent.futures.ProcessPoolExecutor` MUST be used.
- **Mixed or legacy contexts** where `asyncio` cannot be adopted without disproportionate
  refactoring: `concurrent.futures.ThreadPoolExecutor` MAY be used as a transitional
  measure, but MUST be documented with a rationale comment in the domain README.
- A function that performs N ≥ 2 independent I/O or CPU operations sequentially, where
  a concurrent implementation is feasible, MUST be refactored before merge.

## Operational Standards

**Cross-platform**: All tools MUST operate correctly on both Linux and Windows. Path
handling via `pathlib.Path` satisfies this requirement for file operations. Any
unavoidable platform divergence MUST be isolated to a dedicated compatibility shim and
documented in the domain's `README.md` — never embedded inline in core logic.

**Python version enforcement**: Any CI or local tooling MUST validate that the active
interpreter is Python 3.10 or greater before executing any script. Scripts SHOULD emit a
clear error and exit non-zero if the version check fails.

## Quality & Compliance

All code changes MUST be reviewed against each applicable Core Principle before merge.
A feature branch MUST NOT be merged if any of the following violations are present:

- A public function, class, or module lacks a docstring
- An inline comment appears where a named function with a docstring is required
- A type hint is absent from any function signature
- A `print()` call appears outside an interactive REPL helper
- A path argument uses `str` instead of `pathlib.Path`
- A third-party dependency lacks a pinned entry in the domain's `requirements.txt`
- A hardcoded credential, token, or secret is present anywhere in the committed code
- A destructive operation executes without an explicit flag and pre-action log entry
- Business logic and CLI entry point code are not separated
- N ≥ 2 independent I/O-bound or CPU-bound operations execute sequentially where a
  concurrent implementation (asyncio / ProcessPoolExecutor) is feasible

New domain subdirectories MUST ship with at least one test module covering their core
business logic. The `tests/` directory structure MUST mirror the domain directory
structure at all times.

## Governance

This constitution supersedes all other project conventions and is the authoritative
reference for all engineering decisions in this repository. Any amendment MUST:

1. Increment the version number according to the policy below.
2. Update the `Last Amended` date to the date of the change.
3. Be described in the Sync Impact Report embedded as an HTML comment at the top of
   this file.

**Versioning policy** (semantic):

- **MAJOR**: Backward-incompatible governance changes, principle removals, or
  redefinitions that invalidate existing scripts.
- **MINOR**: New principle or section added, or materially expanded guidance.
- **PATCH**: Clarifications, wording corrections, or non-semantic refinements.

**Compliance review**: Every new domain subdirectory and every substantive script change
MUST pass a self-review against the Core Principles checklist before committing.
The plan-template Constitution Check gate MUST be populated with the current principle
list when generating any implementation plan.

**Version**: 1.1.0 | **Ratified**: 2026-04-27 | **Last Amended**: 2026-04-27
