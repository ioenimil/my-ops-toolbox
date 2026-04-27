# GraphQL Contract: GitHub Organisation Repository Listing

**API**: GitHub GraphQL API v4
**Endpoint**: `https://api.github.com/graphql`
**Auth header**: `Authorization: Bearer <token>`
**Module**: `github/github_client.py`

---

## Query: List Organisation Repositories (paginated)

```graphql
query OrgRepos($org: String!, $after: String) {
  organization(login: $org) {
    repositories(
      first: 100
      after: $after
      orderBy: { field: NAME, direction: ASC }
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        url
        sshUrl
        isFork
        isArchived
        defaultBranchRef {
          name
        }
      }
    }
  }
  rateLimit {
    cost
    remaining
    resetAt
  }
}
```

### Variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `$org` | `String!` | Yes | GitHub organisation login |
| `$after` | `String` | No | Pagination cursor; omit on first page |

### Response shape

```json
{
  "data": {
    "organization": {
      "repositories": {
        "pageInfo": {
          "hasNextPage": true,
          "endCursor": "Y3Vyc29yOnYy..."
        },
        "nodes": [
          {
            "name": "repo-alpha",
            "url": "https://github.com/my-company/repo-alpha",
            "sshUrl": "git@github.com:my-company/repo-alpha.git",
            "isFork": false,
            "isArchived": false,
            "defaultBranchRef": { "name": "main" }
          }
        ]
      }
    },
    "rateLimit": {
      "cost": 1,
      "remaining": 4998,
      "resetAt": "2026-04-27T15:00:00Z"
    }
  }
}
```

---

## Pagination Protocol

1. Execute query with `$after = null`.
2. For each page: collect `nodes`, check `pageInfo.hasNextPage`.
3. If `hasNextPage == true`: set `$after = pageInfo.endCursor`, repeat.
4. If `hasNextPage == false`: listing complete.

---

## Rate Limit Handling Protocol

After every response:

1. Read `rateLimit.remaining`.
2. If `remaining < 50` (configurable threshold):
   a. Parse `rateLimit.resetAt` (ISO 8601 UTC).
   b. Compute `wait_seconds = (resetAt - now).total_seconds() + 5` (5s buffer).
   c. Log: `"GitHub API rate limit reached. Resuming in Xm Ys..."`.
   d. `await asyncio.sleep(wait_seconds)`.
   e. Continue pagination.

---

## Error Cases

| HTTP Status / GraphQL Error | Handling |
|-----------------------------|---------|
| `401 Unauthorized` | Fail fast — invalid or missing token. Surface actionable error. |
| `404` on `organization` field | Fail fast — org not found or not accessible with current token. |
| `403 Forbidden` | Fail fast — token lacks `repo` scope. Surface scope requirement. |
| Transient 5xx | Retry with exponential backoff (shared retry logic from `retry.py`) |
| `RATE_LIMITED` GraphQL error | Treat same as `remaining < 50`; parse `resetAt` from error extensions |
