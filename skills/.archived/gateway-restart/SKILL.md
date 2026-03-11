---
name: gateway-restart
description: Use when the agent needs to restart the gateway after channel configuration changes (e.g. after setting up Slack, Telegram, or other messaging integrations). This triggers an interactive restart card in the dashboard chat.
metadata: { "openclaw": { "emoji": "🔄" } }
---

# Gateway Restart

## When to use

Use this skill when:

- You have made changes to channel configuration (Slack, Telegram, WhatsApp, etc.)
- The gateway needs to restart to apply channel changes
- A messaging integration setup has been completed and the gateway must reload

## How it works

The Pazi dashboard supports inline interactive commands. When you output a special command marker in your response, the dashboard renders the corresponding interactive UI component directly in the chat.

## Command

### Restart the gateway

Output the following command marker on its own line to trigger a gateway restart in the dashboard:

```
PAZI_COMMAND:RESTART_GATEWAY
```

The dashboard will show a loading indicator while the gateway restarts and confirm when complete. Channel changes are applied automatically during the restart.

## Example conversation

**User:** I've finished setting up my Slack bot credentials

**Agent response:**

```
Great, the Slack integration is configured. I'll restart the gateway now to apply the changes.

PAZI_COMMAND:RESTART_GATEWAY
```

## Important notes

- Always provide a brief explanation before outputting the command marker
- The command marker must appear exactly as shown: `PAZI_COMMAND:RESTART_GATEWAY`
- Only output ONE command per message
- After `PAZI_COMMAND:RESTART_GATEWAY`, do not add further text — the restart card will appear where the marker is
