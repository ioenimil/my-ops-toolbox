# Technical Research
## Phase 0: Unknowns & technical approaches

### Decision 1: Filtering implementation logic
**Decision**: Implement a pure Python filtering module utilizing standard library `re` and string methods. 
**Rationale**: Core Principle VI dictates preferring standard library over third-party packages. We can achieve prefix (`str.startswith`), suffix (`str.endswith`), and regex (`re.match` or `re.search`) easily with built-in Python tools. 
**Alternatives considered**: Using generic pattern-matching libraries or file-globbing libraries, but `re` is robust enough and already in the standard library.

### Decision 2: Configuration file format
**Decision**: Use JSON or YAML for the configuration file.
**Rationale**: Python standard library includes `json`. If YAML is strictly required it might need a third-party package (`PyYAML`), but JSON is standard and sufficient for list of rules. We will stick to JSON to avoid external dependencies unless the user already has YAML in the project. Given the project has `requirements.txt` we might use YAML if common, but JSON is safer under Principle VI.
**Alternatives considered**: INI, TOML.

### Decision 3: Concurrency for filtering
**Decision**: Filtering logic is CPU-bound but relatively lightweight. The actual fetching/cloning of repos is I/O bound. The filtering itself can be sequential if it's just evaluating strings in memory, but if we evaluate thousands of repos, we could use `concurrent.futures.ProcessPoolExecutor` or simply keep it sequential if it's trivial (O(N) string matches). Given Principle X, if it's just in-memory string matching over a list, sequential is usually fine, but we must ensure we don't violate the rule. We will apply filtering concurrently if the repository list is retrieved concurrently.
**Rationale**: Principle X mandates concurrency for independent operations. 
**Alternatives considered**: Sequential evaluation (might be flagged by reviewers if deemed a violation, though for pure fast string matching it's often exempt if not a bottleneck).