## Pazi Frontend Actions

### Registered Tools (All Sessions)

These tools work across all session types (text, voice, web, Slack):

| Tool                            | Description                                                                                             |
| ------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `ask_for_credentials`           | Prompt user for credentials (API keys, passwords, tokens). Opens a secure form. Returns entered values. |
| `ask_for_browser_login`         | Prompt user to complete a browser login. Shows link + confirmation. Returns when done.                  |
| `pipedream_request_integration` | Request an OAuth integration connection via Pipedream.                                                  |
| `pipedream_wait_for_connection` | Wait for Pipedream OAuth flow to complete.                                                              |

### Voice-Only Client Tools

Available only during ElevenLabs voice sessions:

| Tool                      | Parameters                             | Description                       |
| ------------------------- | -------------------------------------- | --------------------------------- |
| `show_case_study`         | `topic`, `description`                 | Display a case study card         |
| `task_scheduled`          | `task_name`, `schedule`, `description` | Show task scheduling confirmation |
| `show_sample_report`      | `report_type`, `content`               | Display a sample report preview   |
| `start_slack_integration` | (none)                                 | Trigger Slack integration setup   |
| `get_docs`                | `slug`                                 | Fetch documentation text          |

### Text Markers (PAZI_COMMAND)

Display-only cards rendered from text. Used for non-auth display features:

Format: `PAZI_COMMAND:COMMAND_NAME:key=value:key=value`

| Command           | Parameters                             | Example                                                              |
| ----------------- | -------------------------------------- | -------------------------------------------------------------------- |
| `SLACK_SETUP`     | (none)                                 | `PAZI_COMMAND:SLACK_SETUP`                                           |
| `SHOW_CASE_STUDY` | `topic`, `description`                 | `PAZI_COMMAND:SHOW_CASE_STUDY:topic=AI%20Automation:description=...` |
| `TASK_SCHEDULED`  | `task_name`, `schedule`, `description` | `PAZI_COMMAND:TASK_SCHEDULED:task_name=Daily%20Report:schedule=...`  |

### Rules

- **NEVER use PAZI_COMMAND for credentials or browser login** — use `ask_for_credentials` or `ask_for_browser_login` tools
- Use `ask_for_credentials` for API keys, passwords, tokens
- Use `ask_for_browser_login` when user must log into a site in their browser
- Use Pipedream tools when an OAuth integration is available
- Credential values are sensitive — do not echo them in chat messages
- URL-encode values in text markers (spaces -> `%20`, colons -> `%3A`)
- Only one `PAZI_COMMAND:` marker per message
