---
name: qa-queue
description: >-
  Manage the QA testing queue. Every test needs to go through the queue because we
  cannot run testing sessions in parallel. Use the queue.py script for ALL queue
  operations — never edit qa-queue.json directly.
---

# QA Queue

Only one test runs at a time. Use `queue.py` for all operations — it handles
atomic transitions so items never get dropped.

## Queue Script

**Path:** `skills/qa-queue/queue.py`

**NEVER edit `qa-queue.json` directly.** Always use the script. It guarantees
atomic transitions (complete + promote next in one write).

```bash
QUEUE=skills/qa-queue/queue.py
```

### Commands

#### Get status

```bash
python3 $QUEUE status
```

Output: current test, todo list, blocked list, completed count.

#### Add a new test

```bash
python3 $QUEUE add \
  --id PAZ-XXX \
  --type ticket \
  --description "Short description" \
  --prs "{PLATFORM_REPO}#501,{AGENT_REPO}#141" \
  --env qa \
  --requestedBy <requester> \
  --slackChannel {SLACK_PRIMARY_CHANNEL_ID} \
  --slackThread "1775412000.123456"
```

If nothing is running → sets as `current` immediately.
If something is running → adds to `todo`, prints position.

#### Complete current test

```bash
python3 $QUEUE complete \
  --result "13 PASS, 0 FAIL, 0 BLOCKED" \
  --reportUrl "{S3_REPORTS_URL_BASE}/..."
```

Moves current → completed. **Automatically promotes first todo item to current.**

#### Block current test (needs help)

```bash
python3 $QUEUE block \
  --reason "Needs OAuth credentials to test subscription flow"
```

Moves current → blocked. **Automatically promotes first todo item to current.**
After blocking, also:

1. Update Linear ticket status to Blocked (state ID: `{LINEAR_BLOCKED_STATE_ID}`)
2. Message Slack channel: "⏸️ QA blocked on {id}: {reason} <@{TEAM_LEAD_SLACK_ID}>"

#### Update phase on current test

```bash
python3 $QUEUE update-phase \
  --phase phase3 \
  --notes "Completed TC-1.1 through TC-2.3, 8 PASS so far"
```

#### Edit a field on current test

```bash
python3 $QUEUE edit --field testFolder --value "{TEST_RUNS_DIR}/qa-PAZ-XXX-20260409"
```

#### Cancel current test

```bash
python3 $QUEUE cancel
```

Moves current → completed as CANCELLED. **Automatically promotes next.**

#### Unblock a test

```bash
python3 $QUEUE unblock --id PAZ-XXX
```

If nothing is running → sets as current immediately.
If something is running → adds to front of todo.

#### Start next (watchdog / recovery)

```bash
python3 $QUEUE start-next
```

If current is null and todo has items → promotes first todo to current.
Used by the cron watchdog for orphan recovery.

## Queue Structure

```json
{
  "current": { "id": "PAZ-XXX", "phase": "phase3", ... },
  "todo": [ { "id": "PAZ-YYY", ... } ],
  "blocked": [ { "id": "PAZ-ZZZ", "blockedReason": "...", ... } ],
  "completed": [ { "id": "PAZ-AAA", "result": "...", ... } ]
}
```

| List        | Purpose                                                         |
| ----------- | --------------------------------------------------------------- |
| `current`   | The one test actively running (or null)                         |
| `todo`      | Waiting to run, in order. First item is next.                   |
| `blocked`   | Needs input before continuing                                   |
| `completed` | Finished tests (max 15 — oldest auto-cleaned with test folders) |

## Entry Fields

| Field             | Description                                    |
| ----------------- | ---------------------------------------------- |
| `id`              | Ticket ID (PAZ-XXX) or test name               |
| `type`            | `ticket`, `pr`, `staging`, `production`        |
| `description`     | What's being tested                            |
| `prs`             | Array of PR references                         |
| `testFolder`      | Path to test artifacts                         |
| `phase`           | Current phase: `qa-phase0` through `qa-phase4` |
| `lastPhaseUpdate` | Timestamp of last phase change                 |
| `environment`     | QA or production                               |
| `startedAt`       | When testing started                           |
| `requestedBy`     | Who asked for this test                        |
| `slackChannel`    | Slack channel ID                               |
| `slackThreadTs`   | Slack thread timestamp                         |
| `notes`           | Free text for crash recovery                   |
| `blockedReason`   | Why this test is blocked                       |
| `completedAt`     | When testing finished                          |
| `result`          | Final result summary                           |
| `reportUrl`       | S3 URL of the HTML report                      |

## Cron Watchdog

Every 30 minutes, the watchdog checks:

1. **Stale test:** `current` exists but `lastPhaseUpdate` > 2 hours → crash recovery
2. **Orphaned todo:** `current` is null but `todo` has items → `python3 $QUEUE start-next`
