---
name: pazi-integrations
description: When and how to use Pazi integration tools — credential prompts and browser login prompts.
metadata: { "openclaw": { "emoji": "🔗" } }
---

# Pazi Integrations

## Decision Tree

1. Does the service need API keys, tokens, or passwords?
   - YES → Use `ask_for_credentials`
   - NO → Continue to step 2

2. Does the user need to log into a website?
   - YES → Use `ask_for_browser_login`
   - NO → The service likely doesn't need authentication

## Tool Reference

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
