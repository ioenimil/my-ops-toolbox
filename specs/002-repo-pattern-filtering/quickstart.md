# Quickstart: Repository Filtering by Pattern

This feature provides users with advanced filtering capabilities to select repositories by specific naming patterns (prefixes, suffixes, and regular expressions).

## Overview

The filtering engine parses configuration from either CLI parameters or a localized configuration file and validates them against GitHub repositories case-insensitively.

### Example Configuration File (`filters.json`)

```json
{
  "includes": [
    { "type": "prefix", "pattern": "api-" },
    { "type": "suffix", "pattern": "-service" },
    { "type": "regex", "pattern": "^core-.*-v[0-9]+$" }
  ],
  "excludes": [
    { "type": "prefix", "pattern": "api-legacy-" }
  ]
}
```

### Example Usage (CLI)

```bash
# Filter using exact prefix matching
python -m github.cloner --include-prefix "api-" --include-suffix "-service"

# Filter using complex regular expressions
python -m github.cloner --include-regex "^core-.*-v[0-9]+$"

# Using Configuration File (and combined logic)
python -m github.cloner --filter-config filters.json --include-regex "^custom-app-.*$"
```