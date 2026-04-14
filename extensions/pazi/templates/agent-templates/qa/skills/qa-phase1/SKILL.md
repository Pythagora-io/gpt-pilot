---
name: qa-phase1
description: >-
  Phase 1: Research and Reconnaissance. Use after qa-phase0 is fully executed. Fetch PRs, read the diff, deploy to the QA environment if needed, verify environment health, and smoke-check the feature.
---

# Phase 1: Research & Reconnaissance

**Goal:** Understand what changed, verify the environment works, and confirm the
feature loads before running any tests.

**Before starting:** Read `environment.md` in the template root to resolve all
environment-specific values.

## Hard Rules

1. **Use the `browser` tool for all browser automation.** Use the built-in `browser` tool (snapshot + act) in **headed mode** (not headless). Do NOT use Playwright, `browser_use`, or any external browser automation library.
2. **Test environments: QA/staging or production ONLY.** Never localhost. Never worktrees.

## Full Environment Access

You have **full access to the entire cloud account** used for the QA environment. This
environment exists solely for testing — there is nothing you can break that matters. You
can and should do whatever is needed to set up proper test conditions:

- **MongoDB:** Add credits, change user plans, create/delete users, seed data, reset collections, modify any document
- **Agents & Workspaces:** Create agents, delete agents, modify agent configs, create workspaces, assign workspaces
- **Redis:** Read/write/flush keys as needed
- **EC2 instances:** SSH in, restart containers, edit configs, read logs, check disk/memory
- **S3:** Upload/download/delete files
- **Stripe (test mode):** Create subscriptions, trigger webhooks, modify test data
- **Any other cloud resource:** If it's in the account and you need it for testing, use it

Do not hesitate or ask permission — the entire environment is your testing sandbox.

## Prerequisites

- Pre-QA completed — testing plan exists at `{testFolder}/testing-plan.md`
- Queue shows `phase: "phase1"`

## Workflow

### 1.1 Read the Testing Plan

Read `{testFolder}/testing-plan.md` from the qa-phase0 phase. Understand:

- What's being tested and why
- Reproduction evidence (bugs) — what was broken
- All test cases and their priorities

### 1.2 Fetch PR Details

```bash
gh pr view <number> --repo {GITHUB_ORG}/{PLATFORM_REPO} --json title,body,files,url,state
gh pr diff <number> --repo {GITHUB_ORG}/{PLATFORM_REPO}
```

For companion PRs (agent repo):

```bash
gh pr view <number> --repo {GITHUB_ORG}/{AGENT_REPO} --json title,body,files,url,state
```

Understand:

- What files changed and why
- What the developer did NOT verify
- Architecture decisions
- Dependencies between companion PRs

### 1.3 Classify the Change

- **UI Feature** → needs browser testing via `browser` tool (screenshots)
- **API/Backend** → needs API calls, log inspection, DB checks
- **Infrastructure** → needs log inspection, health checks
- **Mixed** → combine approaches

### 1.4 Deploy to QA Environment (if branch testing)

Follow `skills/qa-deploy/SKILL.md` to deploy the PR branch.

Production testing: skip deployment.

### 1.5 Verify Environment Health

**QA environment:**

```bash
# API health
curl -sf {API_URL}/health

# Check containers
ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP} 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Check for errors
ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP} 'docker logs {API_CONTAINER_NAME} --tail 100 2>&1 | grep -iE "error|fail|crash" | head -20'

# Frontend
ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{FRONTEND_EC2_IP} 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Workspace controller
ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{WS_CONTROLLER_EC2_IP} 'docker ps --format "table {{.Names}}\t{{.Status}}"'
```

**Verify workspace TLS certificate:**

```bash
# Check a pending workspace has valid cert
WS_IP=$(curl -sf {WORKSPACE_CONTROLLER_URL}/api/workspace/status | jq -r '.pending[0].publicIp // empty')
WS_HOST=$(curl -sf {WORKSPACE_CONTROLLER_URL}/api/workspace/status | jq -r '.pending[0].hostname // empty')
if [ -n "$WS_IP" ]; then
  ISSUER=$(echo | openssl s_client -connect $WS_IP:443 -servername $WS_HOST 2>/dev/null | openssl x509 -noout -issuer 2>/dev/null)
  echo "Workspace cert issuer: $ISSUER"
fi
```

**Production:**

```bash
curl -sf {APP_PRODUCTION_URL}/api/health
```

### 1.6 Verify New Code Paths Are Reachable

- If PR adds a hook → check logs for hook registration
- If PR adds a UI component → verify page loads without blank screen
- If PR adds an API endpoint → test it directly
- If PR adds an extension → confirm it loaded in logs
- Check imports resolve
- Check companion PRs are deployed
- Check required config/env vars are set

### 1.7 Smoke Check

**"Does the feature described in the PR actually work at all?"**

- Use the `browser` tool to trace the full user flow once
- Don't run formal tests — just verify the happy path loads
- Take a screenshot with `browser action=screenshot` of the feature working (or not working)
- Save to: `{testFolder}/screenshots/smoke-check/`

**If the feature doesn't load at all, that's a HIGH severity bug. Document it immediately
in the testing plan and notify the developer.**

### 1.8 Set Up Environment for Testing

Based on the testing plan's requirements:

- If tests need specific user state → seed MongoDB
- If tests need Slack → connect it (see `slack-browser-testing` skill if available)
- If tests need specific credits/plan → update customer document
- If tests need Stripe webhooks → set up Stripe CLI listener

**MongoDB:** Via `get_credential(service="{MONGODB_CREDENTIAL_SERVICE}")`
**Redis:** `{REDIS_ENDPOINT}`

### 1.9 Update Queue & Transition

```bash
python3 skills/qa-queue/queue.py update-phase \
  --phase phase1-done \
  --notes "Environment healthy. Feature loads. Ready for phase 2."
```

Proceed to `qa-phase2`.

## Output

After this phase you should have:

- PR details understood (files, architecture, gaps)
- Change classified (UI / API / infra / mixed)
- Environment verified healthy
- Smoke check passed (feature loads)
- Environment set up for testing
- Testing plan still intact from qa-phase0 (not modified here)

## Quick Reference

| Setting           | QA Environment                                                | Production                 |
| ----------------- | ------------------------------------------------------------- | -------------------------- |
| Frontend          | `{APP_URL}`                                                   | `{APP_PRODUCTION_URL}`     |
| API               | `{API_URL}`                                                   | Check production API URL   |
| Login             | Email: `{TEST_ACCOUNT_EMAIL}` / `{TEST_ACCOUNT_PASSWORD}`     | As configured              |
| API SSH           | `ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP}`           | N/A                        |
| Frontend SSH      | `ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{FRONTEND_EC2_IP}`      | N/A                        |
| WS Controller SSH | `ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{WS_CONTROLLER_EC2_IP}` | N/A                        |
| MongoDB           | Via `get_credential(service="{MONGODB_CREDENTIAL_SERVICE}")`  | N/A                        |
| Redis             | `{REDIS_ENDPOINT}`                                            | N/A                        |
| Test account      | `{TEST_ACCOUNT_EMAIL}` / `{TEST_ACCOUNT_PASSWORD}`            | Same or production account |
