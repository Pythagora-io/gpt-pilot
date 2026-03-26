## Pazi Frontend Actions

You can trigger interactive dashboard cards via voice tools or text markers.

### Voice Client Tools

These tools are available during ElevenLabs voice sessions. They display UI cards on the user's dashboard.

| Tool                      | Parameters                             | Description                        |
| ------------------------- | -------------------------------------- | ---------------------------------- |
| `show_case_study`         | `topic`, `description`                 | Display a case study card          |
| `ask_for_credentials`     | `service`, `fields` (comma-separated)  | Prompt user for credentials        |
| `ask_for_browser_login`   | `service`, `url`                       | Prompt user to log in via browser  |
| `task_scheduled`          | `task_name`, `schedule`, `description` | Show task scheduling confirmation  |
| `show_sample_report`      | `report_type`, `content`               | Display a sample report preview    |
| `start_slack_integration` | (none)                                 | Trigger Slack integration setup    |
| `get_docs`                | `slug`                                 | Fetch documentation text (no card) |

### Text Markers (PAZI_COMMAND)

Emit a marker in a text message. The frontend parses it and renders the corresponding card.

Format: `PAZI_COMMAND:COMMAND_NAME:key=value:key=value`

URL-encode values to avoid ambiguity with the colon delimiter.

| Command                 | Parameters                             | Example                                                                                 |
| ----------------------- | -------------------------------------- | --------------------------------------------------------------------------------------- |
| `SLACK_SETUP`           | (none)                                 | `PAZI_COMMAND:SLACK_SETUP`                                                              |
| `SHOW_CASE_STUDY`       | `topic`, `description`                 | `PAZI_COMMAND:SHOW_CASE_STUDY:topic=AI%20Automation:description=How%20Pazi%20automates` |
| `ASK_FOR_CREDENTIALS`   | `service`, `fields`                    | `PAZI_COMMAND:ASK_FOR_CREDENTIALS:service=GitHub:fields=token,password`                 |
| `ASK_FOR_BROWSER_LOGIN` | `service`, `url`                       | `PAZI_COMMAND:ASK_FOR_BROWSER_LOGIN:service=CellKeys:url=https%3A%2F%2Fexample.com`     |
| `TASK_SCHEDULED`        | `task_name`, `schedule`, `description` | `PAZI_COMMAND:TASK_SCHEDULED:task_name=Daily%20Report:schedule=Every%20day%20at%209am`  |

### Rules

- URL-encode values in text markers (spaces -> `%20`, colons -> `%3A`).
- Only emit one `PAZI_COMMAND:` marker per message.
- Prefer voice tools during ElevenLabs sessions.
- The card is automatically dismissed when the user sends their next message.
