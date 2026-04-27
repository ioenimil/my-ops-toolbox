"""Exclusion rule construction and matching for github-org-cloner."""

from __future__ import annotations

from github.models import (
    ExactRule,
    ExclusionRule,
    GlobRule,
    PrefixRule,
    SuffixRule,
)


def build_rules(
    prefixes: list[str] | None = None,
    suffixes: list[str] | None = None,
    names: list[str] | None = None,
    patterns: list[str] | None = None,
) -> list[ExclusionRule]:
    """Build a list of ExclusionRule instances from the provided filter values.

    Each non-empty string in a list produces one rule of the corresponding type.
    An empty or None list produces no rules for that type. Returns a flat list
    of all constructed rules.
    """
    rules: list[ExclusionRule] = []
    for prefix in prefixes or []:
        if prefix:
            rules.append(PrefixRule(prefix=prefix))
    for suffix in suffixes or []:
        if suffix:
            rules.append(SuffixRule(suffix=suffix))
    for name in names or []:
        if name:
            rules.append(ExactRule(value=name))
    for pattern in patterns or []:
        if pattern:
            rules.append(GlobRule(pattern=pattern))
    return rules


def matches_any(repo_name: str, rules: list[ExclusionRule]) -> bool:
    """Return True if repo_name matches at least one exclusion rule.

    Returns False immediately if the rules list is empty. Short-circuits on
    the first matching rule.
    """
    return any(rule.matches(repo_name) for rule in rules)
