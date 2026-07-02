# Project memory (Dakera integration)

Pythagora builds applications iteratively across many separate conversations. Each new
conversation re-loads project context from the spec and the file tree, but the
*reasoning* from earlier sessions — architectural decisions, debugging resolutions and
conventions that were agreed on — is not carried over and gets re-derived from scratch.

The optional **project memory** integration gives Pythagora a lightweight, self-hosted
semantic memory backed by a [Dakera](https://dakera.ai) server:

- **On task breakdown**, Pythagora recalls the decisions and bug fixes most relevant to
  the current task and offers them to the Developer agent as extra context (e.g. *"the
  user schema needs `Optional` types to avoid a Pydantic validation error"*).
- **On task completion**, Pythagora stores a short summary of the outcome — including
  any problem → solution pairs from the debugging iterations.

Memories are namespaced per project (`agent_id = "gptpilot-<project_id>"`), so recall
only ever surfaces knowledge from the same project.

## Enabling it

The feature is **off by default**. If the `memory` section is omitted from your config,
Pythagora behaves exactly as before.

1. Run a Dakera server. The canonical path is the docker-compose in
   [`dakera-ai/dakera-deploy`](https://github.com/dakera-ai/dakera-deploy) (the server
   listens on port `3000`).
2. Add a `memory` section to your `config.json`:

   ```json
   "memory": {
     "base_url": "http://localhost:3000",
     "api_key": "dk-your-key",
     "top_k": 5
   }
   ```

| Field             | Default                  | Description                                                        |
| ----------------- | ------------------------ | ------------------------------------------------------------------ |
| `enabled`         | `true`                   | Set to `false` to keep the section but disable the feature.        |
| `base_url`        | `http://localhost:3000`  | Base URL of the Dakera server.                                     |
| `api_key`         | `null`                   | Sent as the `X-API-Key` header (looks like `dk-...`).              |
| `top_k`           | `5`                      | Maximum number of prior memories recalled per task.               |
| `min_importance`  | `0.6`                    | Importance weight assigned to stored task outcomes (`0.0`–`1.0`).  |
| `connect_timeout` | `10.0`                   | Connection timeout in seconds.                                     |
| `read_timeout`    | `20.0`                   | Read timeout in seconds.                                           |

## Failure behaviour

Every call to the memory server is **best-effort**. If the server is slow, unreachable
or returns an error, Pythagora logs a warning and continues with no memory — exactly the
way it degrades when the external documentation API is unavailable. Memory can never
block or fail a build.
