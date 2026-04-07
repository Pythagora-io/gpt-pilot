# Agent (OpenClaw Gateway) — Dev Environment

The agent gateway doesn't need template config files — it's configured via environment variables at startup and the shared `~/.openclaw-dev/openclaw.json`.

## Starting the Gateway

```bash
OPENCLAW_GATEWAY_PORT=<port> \
OPENCLAW_GATEWAY_TOKEN=<token> \
ANTHROPIC_API_KEY=<key> \
ANTHROPIC_BASE_URL=http://127.0.0.1:8765 \
OPENCLAW_SKIP_CHANNELS=1 \
npm run gateway:dev
```

### Environment Variables

| Variable                   | Required | Description                                                      |
| -------------------------- | -------- | ---------------------------------------------------------------- |
| `OPENCLAW_GATEWAY_PORT`    | ✅       | Must match the API's `OPENCLAW_GATEWAY_PORT`                     |
| `OPENCLAW_GATEWAY_TOKEN`   | ✅       | Must match the API's `OPENCLAW_GATEWAY_TOKEN`                    |
| `ANTHROPIC_API_KEY`        | ✅       | Direct API key, or use with `ANTHROPIC_BASE_URL` for proxy       |
| `ANTHROPIC_BASE_URL`       | ❌       | Set to `http://127.0.0.1:8765` if using the main gateway's proxy |
| `OPENCLAW_SKIP_CHANNELS=1` | ❌       | Skip Slack/Telegram/etc. in dev (recommended)                    |
| `PAZI_API_URL`             | ❌       | Points to the Pazi API (default: uses env or config)             |

### Gateway Config

The gateway reads `~/.openclaw-dev/openclaw.json` in dev mode. The Pazi repo's `dev-env/setup.sh` handles updating this file. Two settings matter:

- **`gateway.controlUi.allowedOrigins`** — must include `https://<hostname>:<ssl-port>`
- **`gateway.controlUi.dangerouslyDisableDeviceAuth`** — must be `true` for non-localhost

### Helper Script

Use `start-gateway.sh` for convenience:

```bash
./dev-env/start-gateway.sh --port 13050 --token <token>
```
