---
name: infra-debugging
description: Infrastructure debugging and troubleshooting. Use when investigating any issue — service outages, deployment failures, error spikes, performance problems, state inconsistencies. Contains a searchable database of past issues with resolutions. When you fix a new issue, ADD it to the appropriate reference file. Triggers on "debug", "fix", "broken", "not working", "error", "investigate", "troubleshoot", "down", "failing", "503", "504", "timeout", "slow", "crash".
---

# Debugging Helper

Search the issue database by service area. **After resolving any new issue, add it to the references with symptoms, root cause, resolution, and prevention.**

## Quick Triage

| Symptom             | Check first                                                         |
| ------------------- | ------------------------------------------------------------------- |
| Service unreachable | Is the process running? Check health endpoint. Check load balancer. |
| 5xx errors          | Application logs, recent deploys, database connectivity             |
| Slow responses      | Database queries, external API latency, resource utilization        |
| High error rate     | Monitoring tool (Sentry/equivalent), recent code changes            |
| Can't connect to DB | Credentials valid? Network access? DB server healthy?               |
| Deploy failed       | CI/CD logs, disk space, dependency issues                           |

## Diagnostic Steps

### 0. Pull Latest Code — ALWAYS

**Before investigating any issue, pull the latest code in every cloned repo.** The issue may already be fixed, or the current code on disk may not match what's deployed. Stale code leads to wrong conclusions.

```bash
# Pull all repos in the workspace (adjust paths to match your setup)
for repo in ~/.openclaw/workspace/*/; do
  if [ -d "$repo/.git" ]; then
    echo "Pulling $(basename $repo)..."
    git -C "$repo" pull --ff-only 2>&1 || echo "  ⚠️ Pull failed for $(basename $repo)"
  fi
done
```

Do this **every time** before reading source code to investigate an issue. Not sometimes — every time.

### 1. Gather Context

- When did it start?
- What changed recently? (deploy, config change, traffic spike)
- Who is affected? (all users, some users, internal only)

### 2. Check the Basics

```bash
# If SSH access is configured:
# Process status
ssh -i ~/.ssh/devops-agent devops-readonly@<ip> 'sudo systemctl status <service>'

# Recent logs
ssh -i ~/.ssh/devops-agent devops-readonly@<ip> 'sudo journalctl -u <service> -n 100 --no-pager'

# Resource usage
ssh -i ~/.ssh/devops-agent devops-readonly@<ip> 'free -h && df -h && uptime'
```

### 3. Check Monitoring

- Error tracking (Sentry or equivalent)
- Logs (centralized logging tool)
- Health endpoints

### 4. Document the Issue

After resolution, add to `references/issues.md`:

```markdown
## ISS-NNN: Brief title

**Date:** YYYY-MM-DD
**Symptoms:** What was observed
**Root cause:** Why it happened
**Resolution:** What fixed it
**Prevention:** How to prevent recurrence
```

## Issue Database

- `references/issues.md` — All past issues with resolutions

## SSH Access

<!-- Updated during onboarding -->

```bash
ssh -i ~/.ssh/devops-agent devops-readonly@<ip>
```

See `infra-architecture` skill → `references/servers.md` for server inventory.
