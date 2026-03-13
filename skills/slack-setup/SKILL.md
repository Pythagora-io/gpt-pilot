---
name: slack-setup
description: Use when the user wants to set up, connect, or integrate Slack with their agent. This skill triggers the interactive Slack setup form in the dashboard chat.
metadata: { "openclaw": { "emoji": "🔧" } }
---

# Slack Integration Setup

## When to use

Use this skill when the user asks to:

- Set up Slack integration
- Connect their agent to Slack
- Configure a Slack bot for their agent
- Integrate Slack with Pazi

## How it works

The Pazi dashboard supports inline interactive commands. When you output a special command marker in your response, the dashboard renders the corresponding interactive UI component directly in the chat.

## Command

### Show the Slack setup form

Output the following command marker on its own line to trigger the interactive Slack setup form in the chat:

```
PAZI_COMMAND:SLACK_SETUP
```

The dashboard will replace this marker with a full interactive Slack setup form that guides the user through:

1. Creating a Slack app at api.slack.com/apps
2. Copying the pre-generated app manifest
3. Entering the App ID, App Token, and Bot Token
4. Configuring access controls (open/closed DM policy, group access)
5. Connecting the bot

After the user submits the form, the gateway automatically restarts to apply the channel changes.

If the user sends a new message instead of filling the form, the form is automatically dismissed and normal conversation continues.

## Default Slack behavior

Once connected, the agent behaves as follows by default. Communicate these defaults to the user so they know what to expect:

- **Thread replies**: The agent always responds in a Slack thread. When someone messages the bot (DM or channel mention), the reply appears as a threaded reply to the original message, keeping conversations organized.
- **Channel access**: The agent can read and respond in any channel it has been added to. Users can invite the bot to channels and mention it with `@BotName` to interact.
- **Group access (default: open)**: The bot can respond in channels and group DMs when mentioned. This is configurable via the setup form.
- **DM access (default: open)**: Any Slack user in the workspace can DM the bot. This can be restricted to specific Slack user IDs via the setup form.

## Example conversation

**User:** I want to connect my agent to Slack

**Agent response:**

```
I'll help you set up Slack integration! I'm opening the setup form for you now. Follow the step-by-step instructions to create your Slack app and connect it.

Once connected, your agent will:
- Reply in Slack threads to keep conversations organized
- Respond in any channel it's added to when mentioned

PAZI_COMMAND:SLACK_SETUP
```

## Important notes

- Always provide a brief explanation before outputting the command marker
- The command marker must appear exactly as shown: `PAZI_COMMAND:SLACK_SETUP`
- Only output ONE command per message
- After `PAZI_COMMAND:SLACK_SETUP`, do not add further text — the form will appear where the marker is
