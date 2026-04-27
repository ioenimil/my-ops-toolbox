import pytest
from github.filtering import match_prefix, match_suffix

def test_match_prefix():
    assert match_prefix("API-Gateway", "api-") is True
    assert match_prefix("frontend-app", "api-") is False

def test_match_suffix():
    assert match_suffix("service-API", "-api") is True
    assert match_suffix("service-app", "-api") is False

import json
from pathlib import Path
from github.filtering import parse_filtering_config, filter_repositories
from github.models import Repository, FilteringConfig, FilteringRule, PatternType, FilterAction

def test_parse_filtering_config(tmp_path: Path):
    config_file = tmp_path / "filter.json"
    config_file.write_text(json.dumps({
        "includes": [
            {"pattern_type": "prefix", "pattern": "api"}
        ],
        "excludes": [
            {"pattern_type": "suffix", "pattern": "test"}
        ]
    }))
    
    config = parse_filtering_config(config_file)
    assert len(config.includes) == 1
    assert config.includes[0].pattern_type == PatternType.PREFIX
    assert len(config.excludes) == 1
    assert config.excludes[0].pattern_type == PatternType.SUFFIX

def test_filter_repositories():
    repos = [
        Repository(name="api-gateway", clone_url="", ssh_url="", is_fork=False, is_archived=False, default_branch=""),
        Repository(name="frontend-app", clone_url="", ssh_url="", is_fork=False, is_archived=False, default_branch=""),
        Repository(name="api-test", clone_url="", ssh_url="", is_fork=False, is_archived=False, default_branch="")
    ]
    
    config = FilteringConfig(
        includes=[FilteringRule(PatternType.PREFIX, "api", FilterAction.INCLUDE)],
        excludes=[FilteringRule(PatternType.SUFFIX, "test", FilterAction.EXCLUDE)]
    )
    
    filtered = filter_repositories(repos, config=config)
    assert len(filtered) == 1
    assert filtered[0].name == "api-gateway"

from github.filtering import match_regex

def test_match_regex():
    assert match_regex("api-service", r"^api-.*") is True
    assert match_regex("web-service", r"^api-.*") is False
    assert match_regex("DATA-pipeline", r"data-") is True
    
    # Invalid regex graceful failure
    assert match_regex("api-service", r"^[api") is False
