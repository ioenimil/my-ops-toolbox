def match_prefix(name: str, prefix: str) -> bool:
    """Check if name starts with prefix, case-insensitive."""
    return name.lower().startswith(prefix.lower())


def match_suffix(name: str, suffix: str) -> bool:
    """Check if name ends with suffix, case-insensitive."""
    return name.lower().endswith(suffix.lower())


import json
from pathlib import Path
from github.models import FilteringConfig, FilteringRule, PatternType, FilterAction


def parse_filtering_config(filepath: Path | str) -> FilteringConfig:
    """Parse a JSON configuration file into a FilteringConfig object."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    config = FilteringConfig(includes=[], excludes=[])

    for rule_data in data.get("includes", []):
        ptype = PatternType[rule_data["pattern_type"].upper()]
        config.includes.append(
            FilteringRule(
                pattern_type=ptype,
                pattern=rule_data["pattern"],
                action=FilterAction.INCLUDE,
            )
        )

    for rule_data in data.get("excludes", []):
        ptype = PatternType[rule_data["pattern_type"].upper()]
        config.excludes.append(
            FilteringRule(
                pattern_type=ptype,
                pattern=rule_data["pattern"],
                action=FilterAction.EXCLUDE,
            )
        )

    return config


def filter_repositories(
    repos,
    prefix_includes=None,
    suffix_includes=None,
    regex_includes=None,
    config: FilteringConfig | None = None,
):
    """Filter a list of repositories based on inclusion/exclusion rules."""
    prefix_includes = prefix_includes or []
    suffix_includes = suffix_includes or []
    regex_includes = regex_includes or []

    includes = list(config.includes) if config else []
    excludes = list(config.excludes) if config else []

    for p in prefix_includes:
        includes.append(FilteringRule(PatternType.PREFIX, p, FilterAction.INCLUDE))
    for s in suffix_includes:
        includes.append(FilteringRule(PatternType.SUFFIX, s, FilterAction.INCLUDE))
    for r in regex_includes:
        includes.append(FilteringRule(PatternType.REGEX, r, FilterAction.INCLUDE))

    filtered_repos = []
    for repo in repos:
        name = repo.name

        # 1. Check exclusions first (exclusions triumph)
        is_excluded = False
        for rule in excludes:
            if rule.pattern_type == PatternType.PREFIX and match_prefix(
                name, rule.pattern
            ):
                is_excluded = True
                break
            elif rule.pattern_type == PatternType.SUFFIX and match_suffix(
                name, rule.pattern
            ):
                is_excluded = True
                break
            elif rule.pattern_type == PatternType.REGEX and match_regex(
                name, rule.pattern
            ):
                is_excluded = True
                break

        if is_excluded:
            continue

        # 2. Check inclusions
        # If there are no inclusion rules, we include everything not excluded.
        if not includes:
            filtered_repos.append(repo)
            continue

        is_included = False
        for rule in includes:
            if rule.pattern_type == PatternType.PREFIX and match_prefix(
                name, rule.pattern
            ):
                is_included = True
                break
            elif rule.pattern_type == PatternType.SUFFIX and match_suffix(
                name, rule.pattern
            ):
                is_included = True
                break
            elif rule.pattern_type == PatternType.REGEX and match_regex(
                name, rule.pattern
            ):
                is_included = True
                break

        if is_included:
            filtered_repos.append(repo)

    return filtered_repos


import re
import logging

logger = logging.getLogger(__name__)


def match_regex(name: str, pattern: str) -> bool:
    """Check if name matches the regex pattern, case-insensitive."""
    try:
        return bool(re.search(pattern, name, re.IGNORECASE))
    except re.error as e:
        logger.warning("Invalid regex '%s': %s", pattern, e)
        # Graceful failure for invalid regex
        return False
