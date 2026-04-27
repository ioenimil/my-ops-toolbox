# CLI Contract: github-org-cloner

**Entry point**: `python -m github.org_cloner` (or installed script `github-org-cloner`)
**Module**: `github/org_cloner.py`

---

## Synopsis

```
github-org-cloner [-h] [-o OUTPUT_DIR] [--exclude-prefix PREFIX]
                  [--exclude-suffix SUFFIX] [--exclude NAME]
                  [--exclude-pattern PATTERN]
                  [--protocol {https,ssh}]
                  [--max-concurrent N]
                  [--verbose]
                  ORG
```

---

## Positional Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `ORG` | `str` | Yes | GitHub organisation login name (e.g., `my-company`) |

---

## Optional Arguments

| Flag | Type | Default | Repeatable | Description |
|------|------|---------|-----------|-------------|
| `-o`, `--output-dir` | `Path` | `./<ORG>` | No | Target directory; created if absent |
| `--exclude-prefix` | `str` | — | Yes | Exclude repos whose name starts with this value |
| `--exclude-suffix` | `str` | — | Yes | Exclude repos whose name ends with this value |
| `--exclude` | `str` | — | Yes | Exclude repo by exact name |
| `--exclude-pattern` | `str` | — | Yes | Exclude repos matching a glob pattern (`*`, `?`) |
| `--protocol` | `{https,ssh}` | `https` | No | Clone URL protocol to use |
| `--max-concurrent` | `int` | `5` | No | Maximum parallel git operations (1–50) |
| `--verbose` | flag | off | No | Stream per-repo status; enable DEBUG logging |
| `-h`, `--help` | flag | — | No | Show help and exit 0 |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All processed repositories succeeded (cloned, updated, or up-to-date) |
| `1` | One or more repositories failed after all retries, or a fatal error occurred |

---

## Standard Output Behaviour

**Default (no `--verbose`)**:

```
Syncing organisation: my-company (42 repositories)

Summary
-------
Cloned:           12
Updated:           8
Up to date:       18
Skipped (excl.):   3
Skipped (dirty):   1
Failed:            0
Total:            42
```

**With `--verbose`**:

```
Syncing organisation: my-company (42 repositories)
[✓] cloned    my-company/repo-alpha
[✓] updated   my-company/repo-beta
[~] up-to-date my-company/repo-gamma
[!] skipped (dirty)  my-company/repo-delta — uncommitted changes detected
[✗] failed    my-company/repo-epsilon — git clone exited with code 128 (attempt 3/3)
...

Summary
-------
...
```

**Rate-limit pause (both modes)**:

```
GitHub API rate limit reached. Resuming in 4m 32s...
```

**Error output** (stderr):

```
ERROR: No GitHub token found. Set the GITHUB_TOKEN environment variable
       or run `gh auth login` to authenticate.
```

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `GITHUB_TOKEN` | GitHub personal access token. Takes precedence over `gh` CLI token store. |

---

## Usage Examples

```bash
# Clone all repos from my-company into ./my-company/
github-org-cloner my-company

# Clone into a specific directory
github-org-cloner my-company -o ~/work/my-company

# Exclude archived repos (by prefix convention) and test repos
github-org-cloner my-company --exclude-prefix archive- --exclude-prefix test-

# Exclude a specific repo and a pattern
github-org-cloner my-company --exclude internal-sandbox --exclude-pattern "*-deprecated"

# Use SSH clone URLs, 10 parallel git operations, verbose output
github-org-cloner my-company --protocol ssh --max-concurrent 10 --verbose
```
