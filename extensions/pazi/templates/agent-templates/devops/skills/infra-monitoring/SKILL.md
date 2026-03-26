---
name: infra-monitoring
description: Infrastructure monitoring and health checking. Use for routine health checks, log analysis, error tracking, anomaly detection, and alert management. Covers all connected monitoring tools. For fixing issues found during monitoring, switch to infra-debugging. Triggers on "health check", "monitor", "status", "is everything ok", "any issues", "scan", "errors", "alerts", "logs", "metrics", "uptime", "Sentry", "Datadog", "Grafana", "PostHog".
---

# Monitoring Playbook

## Quick Health Check

<!-- Updated during onboarding with actual commands -->

_Not yet configured. Connect monitoring tools during onboarding._

## Observability Stack

<!-- List all monitoring tools with how to access them -->

| Tool              | What it covers   | Access method                       |
| ----------------- | ---------------- | ----------------------------------- |
| _example: Sentry_ | _Runtime errors_ | _Pipedream integration / API token_ |

**Prefer Pipedream integrations** over direct API calls where available. Use `pipedream_find_integrations` to check if a tool is supported.

## What "Normal" Looks Like

<!-- Baseline metrics — what healthy looks like for this infrastructure -->

| Metric              | Normal    | Problem            |
| ------------------- | --------- | ------------------ |
| _API error rate_    | _< 2%_    | _> 5% sustained_   |
| _Response time p95_ | _< 500ms_ | _> 2s_             |
| _Health endpoints_  | _200 OK_  | _Timeout or error_ |

_Baselines not yet established. Update after initial monitoring period._

## Health Check Commands

<!-- Specific commands for checking each service -->

### HTTP Health Checks

```bash
# Template — update with actual endpoints
curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health
curl -s -o /dev/null -w "%{http_code}" https://app.example.com/
```

### Server Checks (if SSH configured)

```bash
ssh -i ~/.ssh/devops-agent devops-readonly@<ip> 'uptime && free -h && df -h'
```

### Database Checks

```bash
# Run connection tests
python3 skills/devops-onboarding/scripts/test_connections.py mongodb $MONGODB_URL
python3 skills/devops-onboarding/scripts/test_connections.py redis $REDIS_HOST $REDIS_PORT $REDIS_PASSWORD
```

## Log Investigation

<!-- How to query logs from the centralized logging tool -->

_Not yet configured. Document log query patterns after monitoring tools are connected._

## Alert Thresholds

<!-- What constitutes each severity level -->

| Severity          | Criteria                                     | Response                    |
| ----------------- | -------------------------------------------- | --------------------------- |
| **P0 — Critical** | Service down, data loss risk                 | Immediate — wake someone up |
| **P1 — High**     | Degraded service, user-facing impact         | Within 1 hour               |
| **P2 — Medium**   | Non-critical errors, performance degradation | Within 24 hours             |
| **P3 — Low**      | Cosmetic, non-urgent improvements            | Next sprint                 |

## When Issues Are Found

1. Use `infra-debugging` skill for resolution steps
2. Document the issue in `infra-debugging/references/issues.md`
3. Update baselines if "normal" has changed

## Reference Files

- `references/tool-configs.md` — Detailed config for each monitoring tool (orgs, projects, API endpoints)
