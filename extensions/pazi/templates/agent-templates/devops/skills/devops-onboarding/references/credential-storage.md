# Credential Storage Guide

## .credentials.env Format

All credentials go in `.credentials.env` in the workspace root. **Never hardcode credentials into skill files, docs, scripts, or any other file.**

```bash
# Database connections
MONGODB_URL=mongodb+srv://readonly:password@cluster.example.com/
POSTGRES_HOST=db.example.com
POSTGRES_PORT=5432
POSTGRES_DB=myapp
POSTGRES_USER=readonly
POSTGRES_PASSWORD=...
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_PASSWORD=...

# Code repository
GITHUB_PAT=ghp_xxxxx
GITHUB_ORG=my-org

# Cloud providers
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
HETZNER_API_TOKEN=...
GCP_SERVICE_ACCOUNT_JSON=...

# Monitoring
SENTRY_AUTH_TOKEN=...
SENTRY_ORG=my-org
BETTERSTACK_TOKEN=...
DATADOG_API_KEY=...
POSTHOG_API_KEY=...

# SSH
SSH_KEY_PATH=~/.ssh/devops-agent
```

## Rules

1. **Never hardcode** — always load from `.credentials.env` at runtime
2. **Never log credentials** — sanitize output before printing
3. **Never commit** — `.credentials.env` should be in `.gitignore`
4. **Read-only only** — reject any credential with write permissions
5. **Test before storing** — verify it works and has correct permissions
6. **Document what each key is for** — use comments in the file

## Loading in Scripts

```python
# Python
import os
from pathlib import Path

def load_credentials():
    env_file = Path.home() / ".openclaw" / "workspace" / ".credentials.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()
```

```bash
# Bash
if [ -f "$HOME/.openclaw/workspace/.credentials.env" ]; then
    set -a
    source "$HOME/.openclaw/workspace/.credentials.env"
    set +a
fi
```
