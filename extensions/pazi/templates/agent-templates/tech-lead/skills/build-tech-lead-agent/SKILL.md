---
name: build-tech-lead-agent
description: "Set up the Tech Lead agent by walking the user through connecting Linear (optional), Slack, and agent configuration. Creates the config file that all other skills depend on. Use when the user says 'set up tech lead', 'build tech lead agent', 'configure tech lead', or on first run when tech-lead-config.json doesn't exist."
---

# Build Tech Lead Agent

This skill walks the user through setting up a Tech Lead agent that orchestrates
Developer and QA agents for ticket management. It collects all the IDs, credentials,
and configuration needed, then writes them to a config file that the other skills
(`manage-ticket`, `orchestrate-dev-qa`, `ticket-monitor`) read from.

## Overview

Show the user a checklist at the start and update it as you go:

```
🏗️ Tech Lead Agent Setup

☐ 1. Connect Linear (optional but recommended)
☐ 2. Connect to Slack
☐ 3. Configure Developer agent on Slack
☐ 4. Configure QA agent on Slack
☐ 5. Resolve Linear user IDs (if Linear connected)
☐ 6. Configure Linear workflow states (if Linear connected)
☐ 7. Create ticket monitor cron job
☐ 8. Write config file

Let's go through these one by one.
```

Re-post the checklist with ✅ marks after completing each step.

## Step 1: Connect Linear (Optional)

Ask the user:

```
First up — Linear integration. This lets me manage tickets directly:
move them between states, assign to agents, add comments, and monitor progress.

It's optional — you can still coordinate via Slack without it — but it's
*highly recommended* for the full tech lead experience.

Do you want to connect Linear? (yes/no)
```

**If yes:**

1. Ask the user to create a Linear API key:
   ```
   To connect Linear, I need a personal API key:
   1. Go to Linear → Settings → API → Personal API keys
   2. Create a new key (give it a name like "Tech Lead Agent")
   3. Copy the key and paste it here
   ```
2. Use `ask_for_credentials(service="Linear", fields=["api_key"])` to securely collect it
3. Save the key to a file in the workspace:
   ```bash
   echo "{API_KEY}" > ~/.openclaw/workspace/.linear-api-key
   chmod 600 ~/.openclaw/workspace/.linear-api-key
   ```
4. Verify the key works:
   ```bash
   curl -s "https://api.linear.app/graphql" -X POST \
     -H "Content-Type: application/json" \
     -H "Authorization: {API_KEY}" \
     -d '{"query":"{ viewer { id name email } }"}'
   ```
5. Store: `linearConnected = true`, `linearApiKeyPath = ~/.openclaw/workspace/.linear-api-key`

**If no:**

- Store: `linearConnected = false`
- Skip steps 5 and 6 later
- Note: manage-ticket and orchestrate-dev-qa will work via Slack only (no automatic Linear state changes)

## Step 2: Connect to Slack

Ask the user:

```
Next — Slack. This is how you'll communicate with the Developer and QA agents.

Is this agent already connected to Slack? If not, I can help you set it up.
```

**If already connected:**

1. Verify by checking the current Slack connection:
   ```
   What's the Slack channel where ticket coordination will happen?
   (e.g. #engineering, #dev-tickets, etc.)
   ```
2. Get the channel ID — either the user provides it, or help them find it:
   ```
   You can find the channel ID by right-clicking the channel in Slack →
   "View channel details" → the ID is at the bottom.
   ```
3. Store: `slackChannel`, `slackAccountId` (the OpenClaw account ID for Slack)

**If not connected:**

1. Trigger the `slack-setup` skill to walk them through connecting Slack
2. Once done, continue with channel configuration above

## Step 3: Configure Developer Agent on Slack

```
Now I need to know about your Developer agent.

Is your Developer agent connected to Slack? I need their Slack user ID
so I can tag them in ticket threads.

You can find it by:
1. Go to the agent's profile in Slack
2. Click "More" (⋮) → "Copy member ID"

What's the Developer agent's Slack user ID?
```

Also ask:

```
What's the Developer agent's OpenClaw agent ID?
(This is the agent name used in OpenClaw, e.g. "my-developer")
```

Store: `developerSlackId`, `developerAgentId`

## Step 4: Configure QA Agent on Slack

```
Same thing for your QA agent.

What's the QA agent's Slack user ID?
```

Also ask:

```
What's the QA agent's OpenClaw agent ID?
(e.g. "my-qa-agent")
```

Store: `qaSlackId`, `qaAgentId`

## Step 5: Resolve Linear User IDs (if Linear connected)

**Skip this step if `linearConnected = false`.**

Now we need to find the Linear user IDs for the Developer agent, QA agent,
and the human reviewer (who gets assigned tickets when they're ready for review).

```
Let me look up the Linear user IDs for your agents and reviewer.
```

1. Query Linear for all team members:

   ```bash
   LINEAR_KEY=$(cat ~/.openclaw/workspace/.linear-api-key)
   curl -s "https://api.linear.app/graphql" -X POST \
     -H "Content-Type: application/json" \
     -H "Authorization: $LINEAR_KEY" \
     -d '{"query":"{ users { nodes { id name email } } }"}'
   ```

2. Show the user the list and ask them to identify:

   ```
   Here are the users I found in your Linear workspace:

   1. Alice Smith (alice@company.com) — abc123
   2. Bob Dev (bob@company.com) — def456
   3. QA Bot (qa@company.com) — ghi789
   ...

   Which one is:
   - The Developer agent?
   - The QA agent?
   - The human reviewer (who should be assigned tickets when ready for review)?
   ```

3. Store: `developerLinearId`, `qaLinearId`, `reviewerLinearId`

4. Also get the team ID:
   ```bash
   curl -s "https://api.linear.app/graphql" -X POST \
     -H "Content-Type: application/json" \
     -H "Authorization: $LINEAR_KEY" \
     -d '{"query":"{ teams { nodes { id name } } }"}'
   ```
   Ask the user which team to use if there are multiple.
   Store: `teamId`

## Step 6: Configure Linear Workflow States (if Linear connected)

**Skip this step if `linearConnected = false`.**

Query the team's workflow states:

```bash
curl -s "https://api.linear.app/graphql" -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_KEY" \
  -d '{"query":"{ team(id: \"{TEAM_ID}\") { states { nodes { id name type } } } }"}'
```

Show the user the states and map them:

```
Here are your team's workflow states:

1. Backlog — abc111
2. Todo — abc222
3. In Progress — abc333
4. In Review — abc444
5. Done — abc555
...

I need to map these to the tech lead workflow. Which state should be used for:
- "In Progress" (when developer is working)?
- "QA" (when QA is testing)? If you don't have a QA state, I'll suggest creating one.
- "Ready for Review" (when implementation + QA is complete)?
- "Done" (when fully merged and deployed)?
```

If the team doesn't have a "QA" state, suggest creating one:

```
I don't see a QA state. For the tech lead workflow, having a dedicated QA state
is really useful — it makes it clear when something is being tested vs developed.

Want me to create one? I can add it via the Linear API.
```

Store all state IDs in `linearStates`: `{ backlog, todo, agentTodo, inProgress, qa, readyForReview, done, blocked }`

## Step 7: Create Ticket Monitor Cron Job

```
Almost done! I'm going to set up a cron job that runs every 10 minutes to
monitor active tickets. It checks if the Developer or QA agent has gone quiet
and nudges them if they've stalled.
```

Create the cron job:

```bash
openclaw cron create \
  --schedule "*/10 * * * *" \
  --task "Run the ticket-monitor skill. Check for stalled In Progress and QA tickets. Read config from ~/.openclaw/workspace/tech-lead-config.json. If no active tickets, reply HEARTBEAT_OK immediately." \
  --model sonnet \
  --timeout 300
```

Store the cron job ID from the output: `cronJobId`

## Step 8: Write Config File

Write the complete config:

```bash
cat > ~/.openclaw/workspace/tech-lead-config.json << 'EOF'
{
  "linearConnected": true/false,
  "linearApiKeyPath": "~/.openclaw/workspace/.linear-api-key",
  "slackAccountId": "{SLACK_ACCOUNT_ID}",
  "slackChannel": "{SLACK_CHANNEL_ID}",
  "developerSlackId": "{DEV_SLACK_ID}",
  "qaSlackId": "{QA_SLACK_ID}",
  "developerAgentId": "{DEV_AGENT_ID}",
  "qaAgentId": "{QA_AGENT_ID}",
  "developerLinearId": "{DEV_LINEAR_ID or null}",
  "qaLinearId": "{QA_LINEAR_ID or null}",
  "reviewerLinearId": "{REVIEWER_LINEAR_ID or null}",
  "teamId": "{TEAM_ID or null}",
  "linearStates": {
    "backlog": "{ID or null}",
    "todo": "{ID or null}",
    "agentTodo": "{ID or null}",
    "inProgress": "{ID or null}",
    "qa": "{ID or null}",
    "readyForReview": "{ID or null}",
    "done": "{ID or null}",
    "blocked": "{ID or null}"
  },
  "cronJobId": "{CRON_JOB_ID}",
  "setupCompletedAt": "{ISO_DATE}"
}
EOF
```

## Step 9: Confirm Setup

Show the final checklist:

```
🎉 Tech Lead Agent Setup Complete!

✅ 1. Linear: {Connected / Not connected}
✅ 2. Slack: Connected (channel: #{channel_name})
✅ 3. Developer agent: {agent name} ({Slack ID})
✅ 4. QA agent: {agent name} ({Slack ID})
✅ 5. Linear users: {Mapped / Skipped}
✅ 6. Linear states: {Configured / Skipped}
✅ 7. Ticket monitor: Cron job running every 10 min
✅ 8. Config saved to tech-lead-config.json

You're all set! To manage a ticket, just tag me in a Slack thread and say
"manage PROJ-123" and I'll take it from there.
```

## Notes

- The config file path `~/.openclaw/workspace/tech-lead-config.json` is relative to
  whatever workspace the agent runs in — it resolves automatically.
- All three skills (manage-ticket, orchestrate-dev-qa, ticket-monitor) read from this
  same config file. If values need to change later, just update the config.
- If the user later wants to connect Linear after initially skipping it, they can
  re-run this setup skill and it will fill in the missing fields.
