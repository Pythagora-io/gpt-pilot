---
name: manage-ticket
description: "Kick off management of a Linear ticket implementation. Use when told to manage, start, or oversee a ticket (e.g. 'manage PROJ-300', 'start implementation of this ticket', 'can you manage this ticket?'). Handles: assigning to agents, linking Slack threads, starting development, and setting up monitoring."
---

# Manage Ticket Skill

When asked to manage a Linear ticket, follow these steps in order.

## Prerequisites

- You must be in a **Slack thread** — the user sends you a message in Slack asking to manage a ticket
- You need the **ticket identifier** (e.g. PROJ-300) — either from the message or by asking
- The `build-tech-lead-agent` skill must have been completed first (config file exists)

## Config

All IDs and credentials referenced below come from your config file. Read it at the start:

```bash
cat ~/.openclaw/workspace/tech-lead-config.json
```

The config contains: `linearApiKeyPath`, `slackAccountId`, `slackChannel`, `developerSlackId`, `qaSlackId`, `developerLinearId`, `qaLinearId`, `reviewerLinearId`, `teamId`, and all `linearStates`.

## Step 1: Capture the Slack Thread

The Slack thread you're replying in becomes the coordination thread for this ticket.

1. From the inbound message metadata, extract `topic_id` (thread timestamp) and `chat_id` (channel)
2. Format as: `<channel_id>:<thread_ts>` (e.g. `C0ABC123:1775079176.826329`)
3. You'll store this in a Linear comment in Step 3

## Step 2: Get Ticket Details from Linear

```bash
LINEAR_KEY=$(cat {CONFIG.linearApiKeyPath})

# Fetch the ticket
curl -s "https://api.linear.app/graphql" -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_KEY" \
  -d '{"query":"{ issue(id: \"{TICKET_ID}\") { id identifier title description state { name } assignee { name } team { id } } }"}'
```

Note: for the `issue()` query, use the identifier directly (e.g. "PROJ-300").

## Step 3: Update the Linear Ticket

1. **Add a comment** with the Slack thread link:
   ```
   Slack thread: <channel_id>:<thread_ts>
   Managed by: Tech Lead Agent
   Started: <date>
   ```

2. **Move ticket to "QA"** state (for pre-implementation test planning):
   - QA state ID: `{CONFIG.linearStates.qa}`

3. **Assign to QA agent** for pre-planning:
   - QA Linear user ID: `{CONFIG.qaLinearId}`

## Step 4: Tag QA to Create Pre-Implementation Test Plan

In the same Slack thread, send a message to the QA agent to create a testing plan *before* development starts:

```
message(action=send, channel=slack, accountId={CONFIG.slackAccountId}, target=<channel_id>, threadId=<thread_ts>)

Message: "<@{CONFIG.qaSlackId}> Create a pre-implementation test plan for {TICKET_ID}: {ticket title}. Follow the `linear-ticket-pre-qa` skill.

Ticket description:
{ticket_description}"
```

Wait for QA to post the test plan before proceeding to Step 5.

## Step 5: Assign to Developer and Start Implementation

Once QA's test plan is posted:

1. **Assign to Developer agent** — Set the Developer agent as assignee:
   - Developer Linear user ID: `{CONFIG.developerLinearId}`

2. **Move ticket to "In Progress"** state:
   - In Progress state ID: `{CONFIG.linearStates.inProgress}`

3. **Tag Developer in the Slack thread:**

```
message(action=send, channel=slack, accountId={CONFIG.slackAccountId}, target=<channel_id>, threadId=<thread_ts>)

Message: "<@{CONFIG.developerSlackId}> Implement {TICKET_ID}: {ticket title}. Follow the `linear-ticket-workflow` skill.

Ticket description:
{ticket_description}"
```

## Step 6: Confirm in Thread

Reply in the Slack thread confirming what you did:

```
✅ Managing {TICKET_ID}: {ticket title}
• Slack thread linked in Linear comment
• QA created pre-implementation test plan
• Assigned to Developer agent — implementation starting
• QA will execute tests after implementation is complete
• Monitoring active (cron checks every 10 min)
```

## After Kickoff — Workflow Sequence

1. **QA creates pre-implementation test plan** (Step 4 above) — defines what will be tested
2. **Developer implements** → cron monitors for stalls
3. **Developer creates PR** → verify PR targets the configured target branch and has no merge conflicts
4. **QA executes the test plan** against the implementation (with screenshots/video evidence)
5. **QA passes with full evidence** → Report "ready for merge" to the team humans. **DO NOT MERGE.**

### PR Quality Gates
- PRs **must target the configured target branch** (typically `staging`) — verify this every time
- PRs must have **no merge conflicts** — if conflicts exist, tag Developer to resolve immediately
- Check these as soon as a PR is opened, don't wait for QA

> **🚨 CRITICAL: NEVER tell the Developer agent to merge PRs. Merging is a HUMAN-ONLY action. Agents create PRs — humans merge them. No exceptions.**

The cron job (Ticket Monitor, every 10 min) will:
- Check tickets in *both* "In Progress" AND "QA" states
- Verify the developer agent OR QA agent is actively working (depending on state)
- Nudge in the Slack thread if work stalls (30+ min for dev, 2+ hours for QA)
- QA stalls are just as critical as dev stalls — an unfinished test report blocks the entire pipeline

## ⚠️ CRITICAL: Your Role in Ticket Threads

**Once a ticket is kicked off, DO NOT participate in the thread unless:**
- A task is **stalled** (30+ min inactive) — then send a short nudge only
- You are **explicitly asked** a question by a human
- A **key milestone** is reached (see below) — post a brief status update

**DO NOT:**
- Comment on QA findings or bug reports
- Give instructions to the Developer agent
- Offer technical opinions or code review
- Weigh in on implementation approaches
- React to or acknowledge QA/Developer messages

**QA and Developer coordinate directly with each other. You are a silent monitor — you watch the clock, not the conversation.**

If you receive messages in a ticket thread from QA or Developer agents, respond with `NO_REPLY` unless a human directly asks you something.

### Milestone Status Updates

**Silent monitoring ≠ invisible.** Post a brief 2-3 line status update in the thread at these milestones:
- ✅ PRs opened — confirm they target the correct branch and are conflict-free
- ✅ Bugs found by QA and fixed by Dev — confirm fixes verified
- ✅ QA testing resumed after fixes
- ⏰ QA or Dev goes quiet for 2+ hours — nudge immediately, don't wait longer
- 📊 Final QA report received — summarize pass/fail and next steps

These updates keep the humans informed without cluttering the thread. They should never have to ask "what's happening here?"

## Reference IDs

All IDs are stored in `tech-lead-config.json` and populated by the `build-tech-lead-agent` setup skill. Do not hardcode IDs — always read from config.
