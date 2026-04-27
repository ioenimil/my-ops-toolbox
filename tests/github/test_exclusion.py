"""Unit tests for github.exclusion and github.models ExclusionRule types."""

import pytest

from github.exclusion import build_rules, matches_any
from github.models import ExactRule, GlobRule, PrefixRule, SuffixRule


class TestPrefixRule:
    """Tests for PrefixRule.matches."""

    def test_matches_when_name_starts_with_prefix(self) -> None:
        assert PrefixRule("archive-").matches("archive-foo") is True

    def test_no_match_when_name_does_not_start_with_prefix(self) -> None:
        assert PrefixRule("archive-").matches("foo-archive") is False

    def test_empty_prefix_matches_everything(self) -> None:
        assert PrefixRule("").matches("anything") is True


class TestSuffixRule:
    """Tests for SuffixRule.matches."""

    def test_matches_when_name_ends_with_suffix(self) -> None:
        assert SuffixRule("-deprecated").matches("service-deprecated") is True

    def test_no_match_when_name_does_not_end_with_suffix(self) -> None:
        assert SuffixRule("-deprecated").matches("deprecated-service") is False


class TestExactRule:
    """Tests for ExactRule.matches."""

    def test_matches_exact_name(self) -> None:
        assert ExactRule("internal-sandbox").matches("internal-sandbox") is True

    def test_no_match_for_partial_name(self) -> None:
        assert ExactRule("internal-sandbox").matches("internal-sandbox-2") is False

    def test_case_sensitive(self) -> None:
        assert ExactRule("MyRepo").matches("myrepo") is False


class TestGlobRule:
    """Tests for GlobRule.matches."""

    def test_star_wildcard_matches_any_suffix(self) -> None:
        assert GlobRule("test-*").matches("test-alpha") is True

    def test_star_wildcard_matches_any_prefix(self) -> None:
        assert GlobRule("*-v1").matches("service-v1") is True

    def test_question_mark_matches_single_char(self) -> None:
        assert GlobRule("repo-?").matches("repo-a") is True

    def test_question_mark_does_not_match_multiple_chars(self) -> None:
        assert GlobRule("repo-?").matches("repo-ab") is False

    def test_no_match_when_pattern_does_not_fit(self) -> None:
        assert GlobRule("test-*").matches("prod-service") is False


class TestMatchesAny:
    """Tests for matches_any."""

    def test_returns_true_when_one_rule_matches(self) -> None:
        rules = [PrefixRule("archive-"), SuffixRule("-old")]
        assert matches_any("archive-service", rules) is True

    def test_returns_false_when_no_rule_matches(self) -> None:
        rules = [PrefixRule("archive-"), SuffixRule("-old")]
        assert matches_any("active-service", rules) is False

    def test_empty_rules_always_returns_false(self) -> None:
        assert matches_any("any-repo", []) is False

    def test_short_circuits_on_first_match(self) -> None:
        rules = [ExactRule("target"), ExactRule("should-not-reach")]
        assert matches_any("target", rules) is True


class TestBuildRules:
    """Tests for build_rules."""

    def test_builds_prefix_rules(self) -> None:
        rules = build_rules(prefixes=["arch-", "test-"])
        assert len(rules) == 2
        assert all(isinstance(r, PrefixRule) for r in rules)

    def test_builds_suffix_rules(self) -> None:
        rules = build_rules(suffixes=["-old", "-deprecated"])
        assert all(isinstance(r, SuffixRule) for r in rules)

    def test_builds_exact_rules(self) -> None:
        rules = build_rules(names=["sandbox"])
        assert isinstance(rules[0], ExactRule)

    def test_builds_glob_rules(self) -> None:
        rules = build_rules(patterns=["test-*"])
        assert isinstance(rules[0], GlobRule)

    def test_empty_strings_are_skipped(self) -> None:
        rules = build_rules(prefixes=["", "valid-"])
        assert len(rules) == 1

    def test_none_inputs_produce_no_rules(self) -> None:
        assert build_rules() == []

    def test_mixed_types_produce_combined_list(self) -> None:
        rules = build_rules(prefixes=["arch-"], suffixes=["-old"], names=["sandbox"])
        assert len(rules) == 3
