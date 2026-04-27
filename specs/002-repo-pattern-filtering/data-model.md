# Data Model: Repository Filtering by Pattern

## Entities

### `FilteringRule`
Represents a single inclusion or exclusion pattern rule.

- **Attributes**:
  - `pattern_type` (Enum: `PREFIX`, `SUFFIX`, `REGEX`)
  - `pattern` (str): The literal string or regex pattern (e.g., `'api-*'`, `'.*-service'`)
  - `action` (Enum: `INCLUDE`, `EXCLUDE`)

### `FilteringConfig`
The configuration construct holding all defined rules.

- **Attributes**:
  - `includes` (List[FilteringRule]): Rules that selectively include repositories.
  - `excludes` (List[FilteringRule]): Rules that selectively exclude repositories entirely.

### `Repository`
(From existing system, likely `models.py` in `github/`)
- **Attributes**:
  - `name` (str): The name used for matching rules.
  - *Other metadata (url, size, etc.) unmodified.*