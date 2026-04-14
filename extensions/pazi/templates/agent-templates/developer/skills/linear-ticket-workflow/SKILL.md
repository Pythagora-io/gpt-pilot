---
name: linear-ticket-workflow
description: "Entry point for Linear ticket implementation — spawn a worker instance of yourself to handle the full lifecycle. Use when the user gives a Linear ticket to implement, or says things like 'implement this ticket', 'work on this ticket', 'build this'. This skill MUST always be read first when someone asks you to work on a Linear ticket."
---

# Linear Ticket Workflow

When you receive a Linear ticket, this skill handles it. Your job is simple: set up the basics and spawn a worker instance of yourself.

## What You Do

1. Create the feature directory and checklist
2. Update the Linear ticket status
3. Notify the user
4. Spawn a worker instance of yourself
5. You're done — the coder handles everything from planning through delivery

## Steps

### 1. Create Feature Directory and Checklist

```bash
FEATURE="{feature-slug}"
FEATURE_DIR="$FEATURES_DIR/$FEATURE"
mkdir -p "$FEATURE_DIR/plans"
```

Create `{feature_dir}/checklist.md`:

```markdown
# {TICKET_ID}: {TICKET_TITLE} — Implementation Checklist

## Kickoff

- [ ] Created this checklist
- [ ] Moved ticket to "In Progress"
- [ ] Added start comment on Linear
- [ ] Sent user overview with timeline
- [ ] Spawned worker instance

## Phase 1: Dev Environment Setup

- [ ] Created worktrees (from base branch)
- [ ] Installed dependencies
- [ ] Built project successfully
- [ ] Posted status to Linear

## Phase 2: Planning (Cross-Review)

- [ ] Launched both agents R1 (independent plans)
- [ ] Launched both agents R2 (cross-pollinated plans)
- [ ] Wrote verdict + best-plan.md
- [ ] Generated HTML report
- [ ] Uploaded plans to S3
- [ ] Commented on ticket with plan links
- [ ] Sent report + summary to user
- [ ] Credential check — asked for any new keys/secrets needed (or confirmed none needed)

## Phase 3: Implementation

- [ ] Injected Claude Code skills + MCP config
- [ ] Launched Claude Code
- [ ] Post-implementation: TODOs check, tests

## Phase 4: Delivery

- [ ] Created PR with full template
- [ ] Ran Codex independent review
- [ ] Fix-review loop (max 3 rounds) - make sure that Codex approves
- [ ] Sent final message to user
- [ ] Updated Linear ticket → QA state (assigned to QA agent)
- [ ] Notified reviewer / QA
```

### 2. Update Linear Ticket

1. **Move to "In Progress"** — Use the "In Progress" state ID from your Linear workspace
2. **Add start comment** that includes the Slack thread ID so the Tech Lead monitor can find you:
   - "🚀 Starting implementation. Dev setup → cross-review → implementation → delivery. ETA ~1.5-2 hours."
   - If working from a Slack/chat thread, include the thread reference so others can follow progress

### 3. Send User Overview

Send the user:

1. **What you're doing** — the phases
2. **Timeline** — Dev setup: ~10 min, Cross-review: ~30 min, Implementation: ~30 min, PR + review: ~15 min. Total: ~1.5 hours
3. **What they'll see** — "I'll set up the dev environment first, then run the cross-review and auto-proceed to implementation. You can follow progress on the Linear ticket. I'll deliver a PR with test link when done."

### 4. Spawn Coder Agent

```
sessions_spawn(
  agentId: "<YOUR_AGENT_ID>",  // e.g. "pazi-developer"
  mode: "session",
  task: "Implement Linear ticket {TICKET_ID}: \"{TICKET_TITLE}\".

## Ticket Details
- ID: {TICKET_ID}
- Title: {TICKET_TITLE}
- Description: {TICKET_DESCRIPTION}
- URL: {TICKET_URL}
- Feature slug: {FEATURE}
- Feature directory: {FEATURE_DIR}
- Slack channel: {CHANNEL_ID}
- Slack thread: {THREAD_TS}

## Checklist
Read and maintain: {FEATURE_DIR}/checklist.md

## Start
Read skill: phase-1-dev-environment-setup — and follow it.",
  runTimeoutSeconds: 7200
)
```

### 5. Post Kickoff Notification

1. **Linear comment**: "🔄 Kickoff complete → starting Phase 1 (Dev Environment Setup). Coder agent spawned."
2. **User notification**: "📍 {TICKET_ID}: Kickoff done → worker instance spawned, starting dev environment setup. ETA ~10 min."
3. **Update checklist** — check off all Kickoff items

You're done. The coder handles Phases 1–4.

## Cleanup (After PR Merge/Close)

When the PR is merged or closed, read skill: `linear-ticket-cleanup` — that handles worktree deletion and closing comments.

## Linear State IDs

Retrieve your workspace's state IDs by running:

```bash
python3 scripts/linear_api.py states --team-id <YOUR_TEAM_ID>
```

Then fill in:

- Todo: `<STATE_ID>`
- In Progress: `<STATE_ID>`
- Ready for review: `<STATE_ID>`
- Done: `<STATE_ID>`
