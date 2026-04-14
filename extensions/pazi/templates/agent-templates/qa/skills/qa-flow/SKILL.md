---
name: qa-flow
description: >-
  Entry point for ALL QA testing. Read this skill FIRST whenever starting any test —
  PR testing, staging testing, ticket QA, feature testing, regression testing.
  Describes the full testing pipeline (phase 0-4), what resources you have access to,
  and which skills to use at each step. Testing MUST ALWAYS be done on the QA/staging
  environment unless explicitly told otherwise.
  Triggers: "test PR", "test staging", "QA this", "test this", "run QA", "take this ticket".
---

# QA Flow — Entry Point for All Testing

**Read this skill FIRST.** It tells you the full pipeline, what you have access to, and
which skills to load at each phase.

**Before starting:** Read `environment.md` in the template root to resolve all
environment-specific values (`{APP_URL}`, `{API_URL}`, etc.).

## Default Environment

Unless explicitly told to test on production, **ALL testing happens on your QA/staging
environment.** This is your isolated QA environment — you have full admin access and
can't break anything that matters.

The QA environment URLs, credentials, and infrastructure details are all defined in
`environment.md`. Read it first.

## What You Have Access To

You own the entire QA infrastructure. Use whatever you need — no permissions to ask for.

### Cloud Account

- **Full admin access** via the configured AWS CLI profile
- EC2, S3, ECR, Route53, ElastiCache, IAM — everything

### Platform Services

| Service       | Access                                                                                               |
| ------------- | ---------------------------------------------------------------------------------------------------- |
| API           | `{API_URL}` — SSH via `ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP}`                            |
| Frontend      | `{APP_URL}` — SSH via `ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{FRONTEND_EC2_IP}`                       |
| WS Controller | `{WORKSPACE_CONTROLLER_URL}` — SSH via `ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{WS_CONTROLLER_EC2_IP}` |
| Workspaces    | `*.{domain}` — SSH via `ssh -i {SSH_KEY_PATH} {SSH_USER_WORKSPACE}@<ip>`                             |

### Data & Services

| Resource         | Access                                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------------------------- |
| **MongoDB**      | Via `get_credential(service="{MONGODB_CREDENTIAL_SERVICE}")`                                                        |
| **Redis**        | `{REDIS_ENDPOINT}`                                                                                                  |
| **ECR**          | `{ECR_REGISTRY}/{ECR_PREFIX}`                                                                                       |
| **S3**           | `{S3_PUBLIC_BUCKET}`, `{S3_PRIVATE_BUCKET}`, `{S3_USER_DATA_BUCKET}`                                                |
| **AI Providers** | `get_credential(service="{ANTHROPIC_CREDENTIAL_SERVICE}")`, `get_credential(service="{OPENAI_CREDENTIAL_SERVICE}")` |

### Test Account

- **Email:** `{TEST_ACCOUNT_EMAIL}` / `{TEST_ACCOUNT_PASSWORD}`
- **Login:** `{APP_URL}/login` → Continue with Email

### What You Can Do (examples)

- SSH into any EC2 instance, read logs, restart containers
- Modify MongoDB documents (credits, plans, users, agents)
- Create/delete S3 objects
- Terminate and recreate workspaces
- Change Redis keys (pool size, workspace state)
- Build and deploy any branch to any service
- Create new databases for isolated tests

**Do not hesitate or ask permission — the entire environment is your testing sandbox.**

## The Testing Pipeline

Every test follows this pipeline. Read the skill for each phase as you reach it.

```
qa-flow (this skill — read FIRST)
    │
    ▼
qa-phase0 — Pre-QA Setup
    ├── Check queue (read qa-queue skill)
    ├── Create test folder
    ├── Top up QA credits
    ├── Load knowledge base
    ├── Fetch ticket/PR info
    ├── Reproduce bug (if applicable)
    ├── Write testing plan (testing-plan.md + test-cases.json)
    └── Output: test folder with plan ready
    │
    ▼
qa-phase1 — Research & Reconnaissance
    ├── Read PR diff in detail
    ├── Deploy branch to QA env (qa-deploy skill)
    ├── Verify environment health + TLS certs
    ├── Smoke-check the feature
    └── Output: environment ready, feature loads
    │
    ▼
qa-phase2 — Review & Expand Testing Plan
    ├── Review plan with fresh context from phase 1
    ├── Generate bug hypotheses
    ├── Add test cases (never remove)
    └── Output: expanded test-cases.json
    │
    ▼
qa-phase3 — Execute Tests
    ├── Run ALL test cases (API + browser)
    ├── Take screenshots → save to disk
    ├── Visually verify every screenshot
    ├── Update test-cases.json after each test
    └── Output: all tests have status + evidence
    │
    ▼
qa-phase4 — Report & Deliver
    ├── Generate HTML report with screenshots
    ├── Upload to S3
    ├── Post results to Linear + GitHub
    ├── Update knowledge base
    ├── Update queue → pick next
    └── Output: report delivered, queue updated
```

### Phase Skills

| Phase | Skill                       | When to read        |
| ----- | --------------------------- | ------------------- |
| Setup | `skills/qa-flow/SKILL.md`   | Always first        |
| 0     | `skills/qa-phase0/SKILL.md` | Start of every test |
| 1     | `skills/qa-phase1/SKILL.md` | After phase 0       |
| 2     | `skills/qa-phase2/SKILL.md` | After phase 1       |
| 3     | `skills/qa-phase3/SKILL.md` | After phase 2       |
| 4     | `skills/qa-phase4/SKILL.md` | After phase 3       |

### Supporting Skills

| Skill            | Purpose                                                     | When used                         |
| ---------------- | ----------------------------------------------------------- | --------------------------------- |
| `qa-queue`       | Queue management via `queue.py` script — one test at a time | Phase 0 (start) and Phase 4 (end) |
| `qa-deploy`      | Deploy branches to QA env — Docker build, ECR, SSH          | Phase 1                           |
| `knowledge-base` | Platform docs, bug patterns, test strategies                | Phase 0 and Phase 2               |
| `build-report`   | Generate HTML reports                                       | Phase 4                           |
| `linear`         | Linear ticket API — fetch, update, comment                  | Phase 0 and Phase 4               |

## Key Rules

1. **Always start with qa-phase0.** No exceptions.
2. **Testing plan before testing.** Never run tests without a written plan.
3. **Browser testing is the focus.** Unit tests are GitHub Actions' job.
4. **Screenshots saved to disk.** Not just in memory — files on disk or the test is invalid.
5. **Visually verify screenshots** before marking pass/fail. The screenshot is ground truth.
6. **Update test-cases.json after EVERY test.** It's the source of truth for execution state.
7. **Queue is mandatory.** One test at a time. No parallel testing.
8. **QA environment by default.** Only use production if explicitly asked.

## Infrastructure Quick Reference

### Deploy Commands

```bash
# Build + push to ECR
docker build --no-cache -t {ECR_REGISTRY}/{ECR_PREFIX}/api:<tag> -f api/Dockerfile .
docker push {ECR_REGISTRY}/{ECR_PREFIX}/api:<tag>

# Deploy to EC2
ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP} "
  aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {ECR_REGISTRY}
  docker pull {ECR_REGISTRY}/{ECR_PREFIX}/api:<tag>
  docker stop {API_CONTAINER_NAME}; docker rm {API_CONTAINER_NAME}
  docker run -d --name {API_CONTAINER_NAME} --restart unless-stopped -p 3000:3000 \
    --env-file ~/.env.production {ECR_REGISTRY}/{ECR_PREFIX}/api:<tag>
"

# Frontend needs VITE build args
docker build --no-cache \
  --build-arg VITE_API_URL={API_URL} \
  --build-arg VITE_WEB_APP_URL={APP_URL} \
  -t {ECR_REGISTRY}/{ECR_PREFIX}/frontend:<tag> \
  -f skills/qa-deploy/scripts/Dockerfile.frontend-qa .

# Agent branch → update latest.txt
echo "<branch>" | aws s3 cp - s3://{S3_AGENT_ASSETS_BUCKET}/cloud/latest.txt --profile {AWS_PROFILE}
```

### Workspace Management

```bash
# Pool size
curl -X PUT {WORKSPACE_CONTROLLER_URL}/api/workspace/pool-size \
  -H "Content-Type: application/json" -d '{"poolSize": 1}'

# Status
curl {WORKSPACE_CONTROLLER_URL}/api/workspace/status | jq .

# Terminate all
curl -X POST {WORKSPACE_CONTROLLER_URL}/api/workspace/bulk-terminate \
  -H "Content-Type: application/json" -d '{"status": "pending"}'
```

### Logs

```bash
# API logs
ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP} 'docker logs {API_CONTAINER_NAME} --tail 100'

# WS Controller logs
ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{WS_CONTROLLER_EC2_IP} 'docker logs {WS_CONTROLLER_CONTAINER_NAME} --tail 100'

# Workspace logs
ssh -i {SSH_KEY_PATH} {SSH_USER_WORKSPACE}@<workspace-ip> 'sudo tail -50 /var/log/workspace/boot.log'
```

### MongoDB

```bash
# Connection string via get_credential(service="{MONGODB_CREDENTIAL_SERVICE}")
# Top up credits (adapt collection/field names to your data model)
mongosh "$MONGO_URI" --quiet --eval "
  db.users.updateOne(
    {email: '{TEST_ACCOUNT_EMAIL}'},
    {\$set: {credits: 50000}}
  );
"
```
