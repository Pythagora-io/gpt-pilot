---
name: linear
description: Interact with Linear project management via GraphQL API. Use when the agent needs to create, read, update, or search issues, manage projects, check team status, update issue states, add comments, or perform any Linear-related task. Triggers on phrases like "create a Linear issue", "check Linear tickets", "update the ticket", "what's assigned to me", "move issue to In Progress", "add a comment on Linear", "list Linear projects". Always use this skill's API key (via get_credential) — never hardcode keys.
---

# Linear Skill

Manage Linear workspace via the GraphQL API at `https://api.linear.app/graphql`.

## Authentication

The script auto-resolves the API key in this order:

1. `--api-key` argument (if provided)
2. `LINEAR_API_KEY` environment variable
3. `auth-profiles.json` on disk (`~/.openclaw/agents/<AGENT_ID>/agent/auth-profiles.json`, profile `linear:default`)

**Best practice:** Don't pass `--api-key` at all — let the script read directly from `auth-profiles.json`. This avoids LLM credential hallucination issues.

```bash
# ✅ Preferred — reads key from auth-profiles.json automatically
python3 scripts/linear_api.py viewer

# Also works — explicit key
python3 scripts/linear_api.py viewer
```

## Quick Reference

Use `scripts/linear_api.py` for all operations:

```bash
python3 scripts/linear_api.py <command> [options]
```

### Commands

#### Viewer (whoami)

```bash
python3 scripts/linear_api.py viewer
```

#### List Teams

```bash
python3 scripts/linear_api.py teams
```

#### List Issues

```bash
# All issues for a team
python3 scripts/linear_api.py issues --team-id "TEAM_ID"

# Filter by state
python3 scripts/linear_api.py issues --team-id "TEAM_ID" --state "In Progress"

# Assigned to me
python3 scripts/linear_api.py issues --mine

# With limit
python3 scripts/linear_api.py issues --team-id "TEAM_ID" --limit 25
```

#### Get Issue by ID

```bash
# Accepts both UUID and shorthand (e.g., PAZ-123)
python3 scripts/linear_api.py issue --id "PAZ-123"
```

#### Create Issue

```bash
python3 scripts/linear_api.py create-issue \
  --team-id "TEAM_ID" \
  --title "Bug: login fails on mobile" \
  --description "Detailed description in markdown" \
  --priority 2
```

Optional: `--state-id`, `--assignee-id`, `--label-ids "id1,id2"`, `--project-id`

#### Update Issue

```bash
python3 scripts/linear_api.py update-issue \
  --id "PAZ-123" \
  --state-id "STATE_ID"
```

Optional: `--title`, `--description`, `--priority`, `--assignee-id`

#### Add Comment

```bash
python3 scripts/linear_api.py comment \
  --issue-id "PAZ-123" \
  --body "Comment body in markdown"
```

#### List Workflow States (for a team)

```bash
python3 scripts/linear_api.py states --team-id "TEAM_ID"
```

#### List Labels

```bash
python3 scripts/linear_api.py labels
```

#### List Projects

```bash
python3 scripts/linear_api.py projects
```

#### Search Issues

```bash
python3 scripts/linear_api.py search --query "login bug"
```

#### Raw GraphQL Query

```bash
python3 scripts/linear_api.py raw --query '{ viewer { id name } }'
```

## Common Workflows

### Move issue to a new state

1. Get the team's workflow states: `states --team-id TEAM_ID`
2. Find the target state ID (e.g., "In Progress", "Done")
3. Update the issue: `update-issue --id PAZ-123 --state-id STATE_ID`

### Create an issue and assign it

1. Get teams: `teams`
2. Get the viewer (for self-assignment): `viewer`
3. Create: `create-issue --team-id X --title "..." --assignee-id VIEWER_ID`

## Notes

- All output is JSON to stdout, errors to stderr
- Issue IDs accept both UUID format and shorthand (e.g., `PAZ-123`)
- Pagination: use `--limit` (default 50, max 250 per Linear API)
- Rate limits: Linear allows ~1500 requests/hour for personal API keys; batch when possible
- Markdown is supported in descriptions and comments (including collapsible sections with `+++ Title ... +++`)
