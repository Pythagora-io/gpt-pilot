---
name: local-environment-setup
description: Set up fully running local environments with Docker agent, API, frontend, nginx proxy, and isolated database per feature. Use when spinning up a full local dev instance for testing or development.
metadata: { "openclaw": { "emoji": "🐳" } }
---

# Local Environment Setup Skill

Use the `local-environment-setup` CLI to create fully running, isolated instances with their own API, frontend, Docker agent, nginx proxy, and database. Each feature gets its own ports, database, and Redis DB.

## 🚨 CRITICAL RULE: Never Manually Start Services

**NEVER** run `tmux new-session`, `npm run dev`, or any direct process launch. **ALWAYS** use:

```bash
local-environment-setup stop <FEATURE>
local-environment-setup start <FEATURE>
local-environment-setup verify <FEATURE>   # confirm isolation
```

Your exec shell inherits `OPENCLAW_GATEWAY_PORT=12420` from supervisor. If a worktree API inherits this, any login will overwrite the **production agent's proxy context**, causing 403 `user_id_mismatch` errors.

## Quick Reference

```bash
# Create a new feature environment (port auto-assigned)
local-environment-setup create <FEATURE>

# Create with explicit port override (rarely needed)
local-environment-setup create <FEATURE> --port <SSL_PORT>

# Teardown everything
local-environment-setup destroy <FEATURE>

# Stop/start services without destroying
local-environment-setup stop <FEATURE>
local-environment-setup start <FEATURE>

# See all features and their status
local-environment-setup status

# Verify running APIs have correct env isolation
local-environment-setup verify [FEATURE]

# Validate end-to-end (no browser needed)
local-environment-setup-test <FEATURE>
local-environment-setup-test --all
```

## What `create` Does

1. Saves port assignment to `$FEATURES_DIR/port-assignments.json`
2. Pulls latest changes — fetches and pulls the base branch on primary and secondary repos
3. Creates git worktrees (primary + secondary)
4. Generates `api/.env` with all secrets from base repo
5. Generates `frontend/.env` with `VITE_API_URL`
6. Creates nginx SSL config + reloads nginx
7. Updates `~/.openclaw-dev/openclaw.json` with allowed origins
8. Runs `npm install` + `npx husky` + builds shared packages
9. Starts Docker agent container (OpenClaw gateway — config via env vars + CLI flags only, no host volume mount for `.openclaw`)
10. Starts API in tmux with env var overrides (critical for supervisor isolation)
11. Starts frontend in tmux

Result: app running at `https://<YOUR_HOSTNAME>:<PORT>/dashboard`
Login: use test credentials configured during setup

## Port Rules

Ports auto-assigned from registry (base 5300, step 5). All derived from SSL port:

| Service         | Formula        | Example (SSL 5300) |
| --------------- | -------------- | ------------------ |
| SSL/nginx       | `PORT`         | 5300               |
| Frontend (Vite) | `PORT - 1`     | 5299               |
| API (Express)   | `PORT + 800`   | 6100               |
| Agent (Gateway) | `PORT + 10800` | 16100              |

## Script Locations

| Script                         | Skill source                           | Installed to                                  |
| ------------------------------ | -------------------------------------- | --------------------------------------------- |
| `local-environment-setup`      | `scripts/local-environment-setup`      | `/usr/local/bin/local-environment-setup`      |
| `local-environment-setup-test` | `scripts/local-environment-setup-test` | `/usr/local/bin/local-environment-setup-test` |

### Install / Reinstall

```bash
SKILL_DIR="<this skill's directory>"
sudo cp "$SKILL_DIR/scripts/local-environment-setup" /usr/local/bin/local-environment-setup
sudo cp "$SKILL_DIR/scripts/local-environment-setup-test" /usr/local/bin/local-environment-setup-test
sudo chmod +x /usr/local/bin/local-environment-setup /usr/local/bin/local-environment-setup-test
```

## Docker Isolation

The Docker agent's `.openclaw` directory lives _entirely inside the container_ — no host volume mount. Config is passed via CLI flags (`--port`, `--bind`, `--trusted-proxies`, `--disable-device-auth`) and env vars. This eliminates:

- UID mismatch issues (container UID 1000 vs host UID 1001)
- Any file overlap between the Docker agent and the host's production OpenClaw instance
- The need for `chmod 777` on host directories

The only mount is the agent repo worktree (`-v .../agent:/app:ro`), read-only.

## Troubleshooting

See `references/manual-setup-and-troubleshooting.md` for the full reference on supervisor env leaks, port collisions, and manual setup steps.
