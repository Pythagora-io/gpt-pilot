---
name: pazi-browser-use
description: How to use the browser_use tool for cloud browser sessions, web automation, and data extraction.
metadata: { "openclaw": { "emoji": "🌐" } }
---

# Browser Use

Cloud browser sessions for web interaction, scraping, form filling, and screenshots.

## Actions

| Action           | Description                                     |
| ---------------- | ----------------------------------------------- |
| `run`            | Start an async browsing task (natural language) |
| `session_create` | Open an interactive browser session             |
| `status`         | Poll task or session status                     |
| `snapshot`       | Get page accessibility tree                     |
| `screenshot`     | Capture page as image                           |
| `session_stop`   | Close a session                                 |

## When to Use

- **Use Browser Use** when you need to navigate a website, interact with a UI, scrape data, or the service has no API
- **Use Pipedream** when you need a specific API action and the app is in Pipedream's catalog
- **Use ask_for_browser_login** when you need the USER to log in (not the agent)

## Lifecycle

1. `browser_use(action="run", task="...")` or `browser_use(action="session_create", url="...")`
2. Poll with `browser_use(action="status", taskId="...")`
3. Inspect with `snapshot` or `screenshot`
4. **Always** `session_stop` when done to free resources
