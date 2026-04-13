---
name: ticket-monitor
description: "Monitor the ticket lifecycle and nudge stalled workers. Use when checking ticket status, debugging stalled implementations, or managing the monitoring cron job."
---

# Ticket Monitor

Monitors "In Progress" AND "QA" Linear tickets and nudges stalled workers.

## Config

All IDs and credentials referenced below come from your config file. Read it at the start:

```bash
cat ~/.openclaw/workspace/tech-lead-config.json
```

The config contains: `linearApiKeyPath`, `slackAccountId`, `slackChannel`,
`developerSlackId`, `qaSlackId`, `teamId`, `cronJobId`, and all `linearStates`.

## How It Works

**OpenClaw cron job** runs every 10 minutes (job ID stored in `CONFIG.cronJobId`):

1. **Query Linear API** for "In Progress" AND "QA" tickets on the team
2. **If none → stop immediately** (minimal token usage)
3. **If tickets found** → for each, check if the responsible agent is actively working:
   - "In Progress" → check Developer agent activity (stall threshold: 30 min)
   - "QA" → check QA agent activity (stall threshold: 30 min)
4. **If stalled** → nudge in the ticket's Slack thread (stored as a Linear comment: `Slack thread: <channel_id>:<thread_ts>`)

## Cron Job Details

- **Schedule:** Every 10 minutes (OpenClaw cron, not system crontab)
- **Model:** Sonnet (cost-efficient for monitoring)
- **Timeout:** 300s
- **Session:** Isolated (no context bleed)

The cron job is created by the `build-tech-lead-agent` setup skill and its ID is stored in the config.

## Stall Detection

A ticket is considered stalled if:

**In Progress tickets (Developer):**

- No active agent session for 30+ min (`sessions_list`, `ps aux`, `tmux`)
- No recent activity in feature directory checklist
- Nudge: tag `<@{CONFIG.developerSlackId}>` (Developer)

**QA tickets (QA agent):**

- No Slack thread activity for 30+ minutes
- QA hasn't posted test results or progress updates
- Nudge: tag `<@{CONFIG.qaSlackId}>` (QA)

## PR Quality Checks

Whenever PRs exist for a ticket, verify:

- **Target branch is correct** (typically `staging`) — never main, never anything else. If wrong, tag Developer to fix immediately.
- **No merge conflicts** — if conflicts exist, tag Developer to rebase/resolve.
- These checks run on every monitor cycle, not just once.

## Nudging

When stalled, the monitor posts in the ticket's Slack thread:

- Tags the responsible agent
- Brief message about what's stalled and how long since last activity
- Thread ID comes from Linear ticket comment (`Slack thread: <channel_id>:<thread_ts>`)

## Querying Linear

```bash
LINEAR_KEY=$(cat {CONFIG.linearApiKeyPath})

# Find In Progress tickets
curl -s https://api.linear.app/graphql -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_KEY" \
  -d '{"query":"{ issues(filter: { team: { id: { eq: \"{CONFIG.teamId}\" } }, state: { id: { eq: \"{CONFIG.linearStates.inProgress}\" } } }) { nodes { identifier title } } }"}'

# Find QA tickets
curl -s https://api.linear.app/graphql -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_KEY" \
  -d '{"query":"{ issues(filter: { team: { id: { eq: \"{CONFIG.teamId}\" } }, state: { id: { eq: \"{CONFIG.linearStates.qa}\" } } }) { nodes { identifier title } } }"}'
```

## Debugging

```bash
# Check recent runs (use cronJobId from config)
openclaw cron runs --id {CONFIG.cronJobId} --limit 5

# Force a run now
openclaw cron run {CONFIG.cronJobId}

# Check job status
openclaw cron list
```

## Reference IDs

All IDs are stored in `tech-lead-config.json` and populated by the `build-tech-lead-agent` setup skill. Do not hardcode IDs — always read from config.
