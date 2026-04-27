# Data Model: GitHub Organisation Repository Cloner

**Phase**: 1 — Design
**Date**: 2026-04-27
**Module**: `github/models.py`

---

## Entities

### Organisation

Identifies the GitHub organisation to sync.

| Field | Type | Constraints |
|-------|------|-------------|
| `name` | `str` | Non-empty; must be a valid GitHub org login (alphanumeric + hyphens) |

---

### Repository

A single repository belonging to the organisation, as returned by the
GitHub GraphQL API.

| Field | Type | Constraints |
|-------|------|-------------|
| `name` | `str` | Non-empty; unique within the organisation |
| `clone_url` | `str` | HTTPS clone URL (e.g., `https://github.com/org/repo.git`) |
| `ssh_url` | `str` | SSH clone URL (e.g., `git@github.com:org/repo.git`) |
| `is_fork` | `bool` | Whether this repo is a fork of another |
| `is_archived` | `bool` | Whether this repo is archived on GitHub |
| `default_branch` | `str` | Name of the default branch (e.g., `main`, `master`) |

**Identity rule**: Two `Repository` instances with the same `name` within the
same org are considered identical. The `name` is used as the local directory
name under the target directory.

---

### ExclusionRule (discriminated union)

A filter applied to repository names. Four subtypes, all sharing the same
interface: `matches(repo_name: str) -> bool`.

#### PrefixRule

| Field | Type | Constraints |
|-------|------|-------------|
| `prefix` | `str` | Non-empty string |

`matches(name)` → `True` if `name.startswith(prefix)`.

#### SuffixRule

| Field | Type | Constraints |
|-------|------|-------------|
| `suffix` | `str` | Non-empty string |

`matches(name)` → `True` if `name.endswith(suffix)`.

#### ExactRule

| Field | Type | Constraints |
|-------|------|-------------|
| `value` | `str` | Non-empty string |

`matches(name)` → `True` if `name == value`.

#### GlobRule

| Field | Type | Constraints |
|-------|------|-------------|
| `pattern` | `str` | Glob pattern; `*` = zero or more chars, `?` = one char |

`matches(name)` → `True` if `fnmatch.fnmatch(name, pattern)`.

---

### Outcome (Enum)

The result of processing a single repository.

| Member | Meaning |
|--------|---------|
| `CLONED` | Repository did not exist locally; was cloned successfully |
| `UPDATED` | Repository existed locally and was brought to the latest state |
| `UP_TO_DATE` | Repository existed locally and had no changes to pull |
| `SKIPPED_EXCLUDED` | Repository matched one or more exclusion rules |
| `SKIPPED_DIRTY` | Repository existed locally with uncommitted changes; update skipped |
| `FAILED` | All retry attempts exhausted; operation ultimately failed |

---

### SyncResult

The outcome record for a single repository after processing.

| Field | Type | Constraints |
|-------|------|-------------|
| `repo_name` | `str` | The repository's `name` |
| `outcome` | `Outcome` | One of the six Outcome members |
| `error` | `str \| None` | Error message if `outcome == FAILED`; `None` otherwise |

---

### RunSummary

Aggregated counts of all SyncResults for one tool invocation.

| Field | Type | Derivation |
|-------|------|------------|
| `cloned` | `int` | Count of results with `outcome == CLONED` |
| `updated` | `int` | Count of results with `outcome == UPDATED` |
| `up_to_date` | `int` | Count of results with `outcome == UP_TO_DATE` |
| `skipped_excluded` | `int` | Count of results with `outcome == SKIPPED_EXCLUDED` |
| `skipped_dirty` | `int` | Count of results with `outcome == SKIPPED_DIRTY` |
| `failed` | `int` | Count of results with `outcome == FAILED` |
| `total` | `int` | Sum of all counts |

**Validation rule**: `total == cloned + updated + up_to_date + skipped_excluded + skipped_dirty + failed`

---

## State Transitions

For each `Repository` during a sync run:

```text
Repository received from API
        │
        ▼
  Apply ExclusionRules
        │
   matches any? ──Yes──► SKIPPED_EXCLUDED
        │
        No
        │
   Local dir exists?
        │
       No ─────────────► clone (with retry) ──success──► CLONED
        │                                   ──fail────► FAILED
        │
       Yes
        │
   Valid git repo?
        │
       No ─────────────► warn + skip ──────────────────► SKIPPED_DIRTY (non-repo conflict warning)
        │
       Yes
        │
   Uncommitted changes?
        │
       Yes ────────────► warn + skip ──────────────────► SKIPPED_DIRTY
        │
       No
        │
   fetch + pull (with retry)
        │
   new commits? ──Yes──► UPDATED
        │
        No ────────────► UP_TO_DATE
```

---

## Relationships

```text
Organisation  1 ──── * Repository
Repository    * ──── * ExclusionRule   (any matching rule excludes the repo)
SyncRun       1 ──── * SyncResult
SyncRun       1 ──── 1 RunSummary
SyncResult    1 ──── 1 Outcome
```
