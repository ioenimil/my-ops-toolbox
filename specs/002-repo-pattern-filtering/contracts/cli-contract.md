# CLI Contract: Repository Filtering by Pattern

## Invocation

The repository filtering utility will expose the following CLI flags for filtering logic, which can be applied to tools that process repos (e.g., `cloner.py` or new scripts).

### Flags

- `--include-prefix <PREFIX>`: Filter repos by prefix. Can be specified multiple times.
- `--include-suffix <SUFFIX>`: Filter repos by suffix. Can be specified multiple times.
- `--include-regex <REGEX>`: Filter repos by full regex. Can be specified multiple times.
- `--filter-config <PATH>`: A path (handled via `pathlib.Path`) to a JSON configuration file containing multiple inclusion/exclusion rules.

*(Any existing exclude logic will be integrated to satisfy FR-010: Exclusions triumph).*

**Return Values**: Exits 0 on successful processing. Exits > 0 if regex is malformed or config file is invalid.