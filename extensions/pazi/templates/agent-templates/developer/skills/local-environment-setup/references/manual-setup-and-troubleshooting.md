# Manual Setup & Troubleshooting Reference

This document explains what the local setup script does under the hood and how to fix things when the automated script fails. Read this when a worktree environment isn't working and you need to understand _why_.

## Architecture Overview

Each feature worktree runs as a fully isolated instance:

| Component        | Base Instance        | Worktree Environment                      |
| ---------------- | -------------------- | ----------------------------------------- |
| OpenClaw gateway | Main production port | Own Docker agent on feature-specific port |
| API/Frontend     | None — agents only   | Local dev servers in tmux                 |
| Database         | Production           | localhost (local, isolated DB)            |
| Managed by       | Supervisor           | tmux sessions + Docker                    |

## ⚠️ CRITICAL: Supervisor Environment Leak

The base OpenClaw instance runs via supervisor, which sets environment variables globally. **`dotenv` does NOT override existing env vars.** These leak into every child process (tmux, Docker, etc.) and cause cascading failures.

### Inherited Env Vars That MUST Be Overridden

| Variable                          | What breaks if not overridden                                                  |
| --------------------------------- | ------------------------------------------------------------------------------ |
| `NODE_ENV`                        | Login cookie flags wrong for local dev                                         |
| `ANTHROPIC_API_KEY`               | Dummy/proxy key forwarded instead of real key                                  |
| `ANTHROPIC_BASE_URL`              | Routes LLM calls through main gateway's proxy                                  |
| `OPENCLAW_GATEWAY_PORT`           | **CATASTROPHIC**: Worktree API calls main gateway, overwriting billing context |
| `OPENCLAW_GATEWAY_TOKEN`          | Cross-contamination between environments                                       |
| API URL env var                   | Agent calls production API instead of local                                    |
| `OPENCLAW_CLI` / `OPENCLAW_SHELL` | Interferes with dev mode                                                       |

### How the Setup Script Handles This

The API tmux command explicitly sets every variable:

```bash
tmux new-session -d -s "${FEATURE}-api" \
    "cd $FEATURES_DIR/$FEATURE/$REPO_NAME && \
    NODE_ENV=development \
    ANTHROPIC_API_KEY=<real-key> \
    ANTHROPIC_BASE_URL=https://api.anthropic.com \
    OPENCLAW_GATEWAY_PORT=<agent-port> \
    OPENCLAW_GATEWAY_TOKEN=<unique-token> \
    OPENCLAW_CLI= \
    OPENCLAW_SHELL= \
    npm run dev 2>&1 | tee /tmp/${FEATURE}-api.log"
```

**Note:** Setting `OPENCLAW_CLI=` and `OPENCLAW_SHELL=` to empty strings effectively unsets them.

### How to Verify Env Vars Are Correct

```bash
# Find the API process PID
PID=$(ss -tlnp | grep <api-port> | grep -oP 'pid=\K[0-9]+' | head -1)

# Check critical env vars
cat /proc/$PID/environ | tr '\0' '\n' | grep -E "NODE_ENV|ANTHROPIC|OPENCLAW_GATEWAY" | sort
```

## Port Allocation

### Formula (derived from SSL port)

| Service                  | Formula        | Example (--port 5230) |
| ------------------------ | -------------- | --------------------- |
| SSL/nginx (public HTTPS) | `PORT`         | 5230                  |
| Frontend (dev server)    | `PORT - 1`     | 5229                  |
| API (Express)            | `PORT + 800`   | 6030                  |
| Agent (Gateway)          | `PORT + 10800` | 16030                 |

### Port Spacing Requirement

The OpenClaw agent gateway allocates additional ports automatically:

- **Gateway port + 2** → Browser control server
- **Gateway port + 3** → Internal service

**SSL ports must be at least 5 apart** to prevent agent port collisions between features.

### Port Assignment File

`$FEATURES_DIR/port-assignments.json`:

```json
{
  "features": {
    "TICKET-200": {
      "sslPort": 5230,
      "fePort": 5229,
      "apiPort": 6030,
      "agentPort": 16030,
      "dbName": "project_ticket_200",
      "gatewayToken": "abc123..."
    }
  }
}
```

## Directory Structure

```
$FEATURES_DIR/<FEATURE>/
├── <repo>/                # Git worktree of primary repo (from base branch)
│   ├── api/.env           # Generated API config with all secrets
│   ├── frontend/.env      # Generated frontend config
│   └── ...
├── <secondary-repo>/      # Git worktree of secondary repo (if applicable)
├── plans/                 # Cross-review plans and implementation notes
├── checklist.md           # Feature checklist (if created by workflow)
└── report.html            # Cross-review report (if created by workflow)

$AGENT_HOMES/<FEATURE>/
└── .openclaw/
    └── openclaw.json      # Docker agent gateway config

/etc/nginx/conf.d/feature-<feature-lowercase>.conf   # SSL reverse proxy
```

## Component Details

### 1. Nginx SSL Proxy

Each feature gets a server block listening on its SSL port. Critical details:

- **`/gateway-ws` must set `Host: localhost`** — the OpenClaw gateway validates the Host header
- **`/api/` strips the prefix** — `rewrite ^/api/(.*) /$1 break;`
- **Socket.IO needs upgrade headers** — `proxy_set_header Upgrade` and `Connection "upgrade"`

### 2. Docker Agent Container

Each feature runs an OpenClaw agent in Docker with `--network host`.

Key configuration:

- **Volume mount**: Mount at `/home/node/.openclaw` (not `/root/.openclaw` — Docker image runs as user `node`)
- **Directory permissions**: `.openclaw` dir may need `chmod 777` if UID mismatch between host and container
- **Real API key**: Pass real Anthropic key, NOT a proxy dummy
- **`trustedProxies`**: Must be at `gateway` level (NOT inside `controlUi`)

### 3. npm Install

**Must use `NODE_ENV=development`** for install. Supervisor sets `NODE_ENV=production` which makes npm skip devDependencies.

```bash
NODE_ENV=development npm install --ignore-scripts
npm run build  # Build shared packages if applicable
```

## Troubleshooting

### Login cookie not being stored

**Cause:** `NODE_ENV=production` leaked from supervisor → cookie flags wrong for local dev.
**Fix:** Verify `NODE_ENV=development` in the API process env.

### WebSocket keeps reconnecting

**Check gateway logs:** `docker logs agent-<FEATURE>` — look for:

- `origin not allowed` → Add origin to gateway config `allowedOrigins`
- `control ui requires device identity` → Set `dangerouslyDisableDeviceAuth: true`
- `Proxy headers detected from untrusted address` → Add `trustedProxies` at `gateway` level

### 401 invalid x-api-key

**Cause:** Dummy/proxy API key leaked from supervisor.
**Fix:** Pass the real key via Docker `-e` flag or tmux env override.

### Docker agent EACCES permission denied

**Cause:** UID mismatch between host user and container user.
**Fix:** `chmod 777` the `.openclaw` directory and restart the container.

### Config validation: "Unrecognized key: trustedProxies"

**Cause:** `trustedProxies` placed inside `gateway.controlUi` instead of at `gateway` level.
**Fix:** Move `trustedProxies` to `gateway.trustedProxies`.

### npm install skips TypeScript / build fails

**Cause:** `NODE_ENV=production` leaked → npm skips devDependencies.
**Fix:** Run `NODE_ENV=development npm install --ignore-scripts`.

### Cleanup fails: rm permission denied on agent-homes

**Cause:** Docker container created directories with different UID than host user.
**Fix:** Use `sudo rm -rf` on the agent-homes directory.

## Validation

Use the test script to validate a worktree end-to-end without a browser:

```bash
local-setup-test <FEATURE>       # Test one feature
local-setup-test --all           # Test all registered features
```

Tests performed:

1. API health check (`GET /health` → 200)
2. Frontend HTML (`GET /` → HTML response)
3. Login (if auth is set up — use test credentials from setup)
4. WebSocket handshake (connect to gateway, authenticate)
