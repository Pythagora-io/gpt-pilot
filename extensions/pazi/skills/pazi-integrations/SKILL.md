---
name: pazi-integrations
description: When and how to use Pazi integration tools — Pipedream OAuth, credential prompts, and browser login prompts.
metadata: { "openclaw": { "emoji": "🔗" } }
---

# Pazi Integrations

## Decision Tree

1. Is there a Pipedream integration for the service?
   - YES → Use `pipedream_find_integrations` → `pipedream_check_integration` → `pipedream_request_integration` + `pipedream_wait_for_connection` if needed
   - NO → Continue to step 2

2. Does the service need API keys, tokens, or passwords?
   - YES → Use `ask_for_credentials`
   - NO → Continue to step 3

3. Does the user need to log into a website?
   - YES → Use `ask_for_browser_login`
   - NO → The service likely doesn't need authentication

## Tool Reference

### Pipedream Flow

1. `pipedream_find_integrations` — ALWAYS call first to find exact app slug
2. `pipedream_check_integration` — Check if already connected
3. `pipedream_request_integration` — Prompt user to connect (if not connected)
4. `pipedream_wait_for_connection` — Wait for OAuth completion
5. `pipedream_list_actions` → `pipedream_get_action` — Discover actions
6. `pipedream_use_integration` — Execute action

### ask_for_credentials

- `service`: Display name of the service
- `fields`: Array of field names (e.g., `["api_key", "api_secret"]`)
- `message`: Why you need the credentials
- Returns: `{ status: "completed", values: { ... } }` or `cancelled`/`timeout`

### ask_for_browser_login

- `service`: Display name of the service
- `url`: Login page URL
- `message`: Instructions for the user
- Returns: `{ status: "completed", confirmed: true }` or `cancelled`/`timeout`

## Rules

- Never echo credential values in chat messages
- Always explain WHY you need credentials using the `message` parameter
- Never use PAZI_COMMAND text markers for credentials or login
- For Pipedream: app slugs are often unexpected (e.g., Slack is `slack_v2`)
