# Tasks: Repository Filtering by Pattern

**Input**: Design documents from `/specs/002-repo-pattern-filtering/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

## Format

- **[P]**: Can run in parallel
- **[Story]**: Which user story this task belongs to (US1, US2)

## Phase 1: Setup

**Purpose**: Project initialization and basic structure

- [X] T001 Create structure for the filtering module by initializing `github/filtering.py`.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

- [X] T002 Implement data models `FilteringRule` and `FilteringConfig` in `github/models.py`.
- [X] T003 Set up `tests/github/test_filtering.py` foundation with initial imports and generic testing fixtures if needed.

## Phase 3: User Story 1 - Apply Prefix and Suffix Filters (Priority: P1) 🎯 MVP

**Goal**: Filter repositories by simple prefixes or suffixes to quickly select groups of related repositories.
**Independent Test**: Can be fully tested by providing simple prefix/suffix strings and verifying only matching repositories are cloned or processed.

### Tests for User Story 1

- [X] T004 [P] [US1] Write unit tests for prefix and suffix matching logic in `tests/github/test_filtering.py`.
- [X] T005 [P] [US1] Write unit tests for JSON config file parsing of prefix/suffix rules in `tests/github/test_filtering.py`.

### Implementation for User Story 1

- [X] T006 [P] [US1] Implement `match_prefix` and `match_suffix` core logic case-insensitively in `github/filtering.py`.
- [X] T007 [P] [US1] Implement JSON configuration parser for `FilteringConfig` in `github/filtering.py`.
- [X] T008 [US1] Implement combined evaluation logic to filter a repository list against prefix/suffix inclusion and exclusion rules in `github/filtering.py` (depends on T006, T007).
- [X] T009 [US1] Update CLI arguments parser in `github/cloner.py` to accept `--include-prefix`, `--include-suffix`, and `--filter-config`.
- [X] T010 [US1] Integrate filtering evaluation before the cloning step in `github/cloner.py`, ensuring exclusions take precedence without breaking idempotency.

## Phase 4: User Story 2 - Apply Regex Filters (Priority: P2)

**Goal**: Support filtering repositories using advanced regular expressions to match complex naming conventions.
**Independent Test**: Can be fully tested by providing regex patterns and verifying that only repositories matching the regex are included, plus validating graceful error handling for invalid regex.

### Tests for User Story 2

- [X] T011 [P] [US2] Add unit tests for regex matching, including cases with valid and invalid patterns, in `tests/github/test_filtering.py`.

### Implementation for User Story 2

- [X] T012 [P] [US2] Implement `match_regex` core logic case-insensitively using standard `re` module in `github/filtering.py`.
- [X] T013 [US2] Update `FilteringConfig` parser to support regex rules and handle graceful failure for invalid syntax in `github/filtering.py`.
- [X] T014 [US2] Update CLI arguments in `github/cloner.py` to accept `--include-regex` and pass it to the combined evaluation logic.

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, documentation, and performance verification.

- [X] T015 Verify concurrency context: ensure in-memory string matching filtering logic does not block fetching/cloning I/O operations in `github/cloner.py`.
- [X] T016 Update `README.md` and module docstrings in `github/filtering.py` to fully document the new filter flags, maintaining Code Standards.
- [X] T017 Final run of `pytest` across all testing modules in `tests/github/` to ensure no regressions.