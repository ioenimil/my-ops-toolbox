# github/

GitHub domain tools for my-ops-toolbox.

---

## github-org-cloner

Clone and synchronise all repositories of a GitHub organisation to a local directory.

### Purpose

A cross-platform CLI tool that lists every accessible repository in a GitHub
organisation via the GraphQL API and either clones (first run) or updates
(subsequent runs) each one in parallel. Exclusion rules let you skip repos by
prefix, suffix, exact name, or glob pattern.

### Prerequisites

- Python 3.10 or greater
- `git` installed and on `PATH`
- A GitHub token with `repo` scope, available via one of:
  - `GITHUB_TOKEN` environment variable, **or**
  - `gh` CLI authenticated (`gh auth login`)

Install the Python dependency:

```bash
cd github
pip install -r requirements.txt
```

### Usage

```bash
python -m github.org_cloner --help
```

#### Initial sync — clone everything

```bash
python -m github.org_cloner my-company
```

Clones all accessible repositories into `./my-company/<repo-name>/`.

#### Custom output directory

```bash
python -m github.org_cloner my-company -o ~/work/clients/my-company
```

#### Incremental update — re-run to stay current

```bash
python -m github.org_cloner my-company
```

Repositories already present are fetched and pulled; new repositories are
cloned; unchanged repositories are reported as up-to-date.

#### Exclude by prefix

```bash
python -m github.org_cloner my-company --exclude-prefix archive- --exclude-prefix test-
```

#### Exclude by suffix

```bash
python -m github.org_cloner my-company --exclude-suffix -deprecated
```

#### Exclude by exact name

```bash
python -m github.org_cloner my-company --exclude internal-sandbox
```

#### Exclude by glob pattern

```bash
python -m github.org_cloner my-company --exclude-pattern "test-*" --exclude-pattern "*-v1"
```

#### SSH clone URLs

```bash
python -m github.org_cloner my-company --protocol ssh
```

Requires SSH keys configured and the SSH agent running.

#### Verbose output — stream per-repo status

```bash
python -m github.org_cloner my-company --verbose
```

#### Control parallel git operations

```bash
python -m github.org_cloner my-company --max-concurrent 10
```

Default is 5. Maximum is 50.

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All repositories processed successfully |
| `1` | One or more repositories failed, or a fatal error occurred |

### Troubleshooting

**Missing token**

```
ERROR: No GitHub token found. Set the GITHUB_TOKEN environment variable
       or run `gh auth login` to authenticate.
```

Set `export GITHUB_TOKEN=<your-token>` or run `gh auth login`.

**Dirty repository warning**

```
WARNING: [skipped] my-repo — uncommitted changes detected; skipping update.
```

Commit or stash changes in the named repository, then re-run the tool.

**Rate limit pause**

```
WARNING: GitHub API rate limit reached. Resuming in 4m 32s...
```

The tool pauses automatically and resumes when the rate limit resets. No
action required.
