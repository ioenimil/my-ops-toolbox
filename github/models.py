"""Data models for the github-org-cloner tool."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Union


@dataclass(frozen=True)
class Organisation:
    """A GitHub organisation identified by its login name."""

    name: str


@dataclass(frozen=True)
class Repository:
    """A single repository belonging to a GitHub organisation."""

    name: str
    clone_url: str
    ssh_url: str
    is_fork: bool
    is_archived: bool
    default_branch: str


class Outcome(Enum):
    """The result of processing a single repository during a sync run."""

    CLONED = auto()
    UPDATED = auto()
    UP_TO_DATE = auto()
    SKIPPED_EXCLUDED = auto()
    SKIPPED_DIRTY = auto()
    FAILED = auto()


@dataclass(frozen=True)
class SyncResult:
    """The outcome record for a single repository after processing."""

    repo_name: str
    outcome: Outcome
    error: str | None = None


@dataclass
class RunSummary:
    """Aggregated counts of all SyncResults for one tool invocation."""

    cloned: int = 0
    updated: int = 0
    up_to_date: int = 0
    skipped_excluded: int = 0
    skipped_dirty: int = 0
    failed: int = 0

    @property
    def total(self) -> int:
        """Return the total number of repositories processed."""
        return (
            self.cloned
            + self.updated
            + self.up_to_date
            + self.skipped_excluded
            + self.skipped_dirty
            + self.failed
        )


@dataclass(frozen=True)
class PrefixRule:
    """Excludes repositories whose names start with the given prefix."""

    prefix: str

    def matches(self, name: str) -> bool:
        """Return True if name starts with this rule's prefix."""
        return name.startswith(self.prefix)


@dataclass(frozen=True)
class SuffixRule:
    """Excludes repositories whose names end with the given suffix."""

    suffix: str

    def matches(self, name: str) -> bool:
        """Return True if name ends with this rule's suffix."""
        return name.endswith(self.suffix)


@dataclass(frozen=True)
class ExactRule:
    """Excludes a repository with an exact matching name."""

    value: str

    def matches(self, name: str) -> bool:
        """Return True if name exactly equals this rule's value."""
        return name == self.value


@dataclass(frozen=True)
class GlobRule:
    """Excludes repositories whose names match a glob pattern (* and ?)."""

    pattern: str

    def matches(self, name: str) -> bool:
        """Return True if name matches the glob pattern."""
        return fnmatch.fnmatch(name, self.pattern)


ExclusionRule = Union[PrefixRule, SuffixRule, ExactRule, GlobRule]
