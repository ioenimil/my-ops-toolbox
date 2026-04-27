# Quickstart: GitHub Organisation Repository Cloner

## Prerequisites

- Python 3.10 or greater
- `git` installed and on `PATH`
- A GitHub token with `repo` scope, available via one of:
  - `GITHUB_TOKEN` environment variable, or
  - `gh` CLI authenticated (`gh auth login`)

## Installation

```bash
# From the repository root
cd github
pip install -r requirements.txt
```

## Verify Setup

```bash
python -m github.org_cloner --help
```

Expected output includes the `ORG` positional argument and all flags.

## First Sync

```bash
# Clone all repositories from my-company into ./my-company/
python -m github.org_cloner my-company
```

The tool will:
1. Resolve your GitHub token.
2. Fetch the full repository list via a GraphQL query.
3. Clone each repository in parallel into `./my-company/<repo-name>/`.
4. Print a summary when complete.

## Incremental Update

Run the same command again. Repositories already present are fetched and
pulled to the latest state; new repositories are cloned; nothing is
re-downloaded unnecessarily.

```bash
python -m github.org_cloner my-company
```

## Filtering with Exclusion Rules

```bash
# Skip repos starting with "archive-" or ending with "-deprecated"
python -m github.org_cloner my-company \
  --exclude-prefix archive- \
  --exclude-suffix -deprecated

# Skip one specific repo and a pattern
python -m github.org_cloner my-company \
  --exclude internal-sandbox \
  --exclude-pattern "test-*"
```

## SSH Clone URLs

```bash
python -m github.org_cloner my-company --protocol ssh
```

Requires SSH keys configured in your SSH agent.

## Verbose Mode

```bash
python -m github.org_cloner my-company --verbose
```

Streams each repository's outcome as it is processed, in addition to the
final summary.

## Custom Output Directory

```bash
python -m github.org_cloner my-company -o ~/work/clients/my-company
```

## Running Tests

```bash
# From the repository root
pytest tests/github/ -v
```

## Validation Checklist

- [ ] `python -m github.org_cloner --help` exits 0 and shows all flags
- [ ] Running against a real org creates one subdirectory per repository
- [ ] Re-running produces the same result without re-cloning
- [ ] `--exclude-prefix archive-` skips repositories starting with `archive-`
- [ ] A repo with uncommitted changes is reported as `skipped (dirty)`
- [ ] Missing `GITHUB_TOKEN` and no `gh auth` produces a clear error on stderr
