---
name: qa-deploy
description: Deploy specific branches to the QA environment. Shared foundation for all QA testing flows — handles Docker builds, ECR push, SSH deployment, health checks, and agent version pinning. Called by qa-phase1 during deployment before any tests run. NOT a standalone skill — always invoked as part of a larger testing flow.
---

# QA Deploy — Environment Setup

Deploy the correct branches to the isolated QA environment before running tests.
This skill is the **shared setup step** for all QA testing flows.

**Before starting:** Read `environment.md` in the template root to resolve all
environment-specific values.

## When to Use

Called automatically at the start of any QA test run. Never invoked directly by the user.

## Prerequisites

- AWS profile configured (see `environment.md`)
- SSH key available (see `environment.md`)
- ECR login (auto-handled by deploy steps)
- Full infra details: see `skills/qa-flow/SKILL.md` (Infrastructure Quick Reference section)

## Quick Reference

| Service       | EC2 IP                   | Container                        | SSH User               |
| ------------- | ------------------------ | -------------------------------- | ---------------------- |
| API           | `{API_EC2_IP}`           | `{API_CONTAINER_NAME}`           | `{SSH_USER_EC2}`       |
| Frontend      | `{FRONTEND_EC2_IP}`      | `{FRONTEND_CONTAINER_NAME}`      | `{SSH_USER_EC2}`       |
| WS Controller | `{WS_CONTROLLER_EC2_IP}` | `{WS_CONTROLLER_CONTAINER_NAME}` | `{SSH_USER_EC2}`       |
| Workspaces    | varies                   | (host supervisor)                | `{SSH_USER_WORKSPACE}` |

ECR: `{ECR_REGISTRY}/{ECR_PREFIX}`

## Input

The calling skill provides a **deploy spec**:

```json
{
  "platform_branch": "feature/voice-transcription",
  "agent_branch": "feature/voice-transcription",
  "platform_repo_path": "{PLATFORM_REPO_PATH}",
  "agent_repo_path": "{AGENT_REPO_PATH}",
  "database": "{MONGODB_DEFAULT_DB}",
  "tag": "pr-501"
}
```

- `platform_branch` — branch for API + Frontend + WS Controller (null = keep current)
- `agent_branch` — branch for workspace agent (null = keep current)
- `platform_repo_path` — path to platform repo or worktree
- `database` — MongoDB database name (default from environment.md, or isolated per-PR)
- `tag` — Docker image tag (used for ECR)

## Step 1: Resolve Source Code

```bash
# Check if branch has a worktree
WORKTREE=$(cd {PLATFORM_REPO_PATH} && git worktree list | grep "<branch>" | awk '{print $1}')
if [ -n "$WORKTREE" ]; then
  REPO_PATH="$WORKTREE"
else
  REPO_PATH="{PLATFORM_REPO_PATH}"
  cd "$REPO_PATH"
  git fetch origin "<branch>"
  git checkout "<branch>"
fi
```

## Step 2: Build & Push Docker Images

**ALWAYS use `--no-cache`** to avoid stale cached layers.

### API

```bash
cd "$REPO_PATH"
docker build --no-cache -t {ECR_REGISTRY}/{ECR_PREFIX}/api:<tag> -f api/Dockerfile .
docker push {ECR_REGISTRY}/{ECR_PREFIX}/api:<tag>
```

### Frontend (requires VITE build args)

```bash
# Custom build with test environment URLs baked in
docker build --no-cache \
  --build-arg BUILD_MODE=production \
  --build-arg VITE_API_URL={API_URL} \
  --build-arg VITE_WEB_APP_URL={APP_URL} \
  -t {ECR_REGISTRY}/{ECR_PREFIX}/frontend:<tag> \
  -f /tmp/Dockerfile.frontend-qa .
```

The custom Dockerfile must pass VITE\_\* as env vars during the Vite build step.
See `skills/qa-deploy/scripts/Dockerfile.frontend-qa` for the template.

### WS Controller (only if WS Controller code changed)

```bash
docker build --no-cache -t {ECR_REGISTRY}/{ECR_PREFIX}/workspace-controller:<tag> -f workspace-controller/Dockerfile .
docker push {ECR_REGISTRY}/{ECR_PREFIX}/workspace-controller:<tag>
```

## Step 3: Deploy to EC2

For each service that was rebuilt:

```bash
ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@<IP> "
  aws ecr get-login-password --region {AWS_REGION} | docker login --username AWS --password-stdin {ECR_REGISTRY} 2>/dev/null
  docker pull {ECR_REGISTRY}/{ECR_PREFIX}/<service>:<tag>
  docker stop <container>; docker rm <container>
  docker run -d --name <container> --restart unless-stopped -p 3000:3000 \
    --env-file ~/.env.production \
    {ECR_REGISTRY}/{ECR_PREFIX}/<service>:<tag>
"
```

**Reminder:** `docker restart` does NOT pick up env changes. Always `stop + rm + run`.

## Step 4: Update Agent Branch (if agent PR)

```bash
# Set latest.txt to branch name — boot.sh uses git clone --branch
echo "<agent_branch>" | aws s3 cp - s3://{S3_AGENT_ASSETS_BUCKET}/cloud/latest.txt --profile {AWS_PROFILE}

# Terminate existing workspaces so new ones boot with the branch
curl -X POST {WORKSPACE_CONTROLLER_URL}/api/workspace/bulk-terminate \
  -H "Content-Type: application/json" -d '{"status": "pending"}'
curl -X POST {WORKSPACE_CONTROLLER_URL}/api/workspace/bulk-terminate \
  -H "Content-Type: application/json" -d '{"status": "booting"}'

# Pool will auto-replenish (pool size should be >= 1)
curl -X PUT {WORKSPACE_CONTROLLER_URL}/api/workspace/pool-size \
  -H "Content-Type: application/json" -d '{"poolSize": 1}'
```

## Step 5: Update Database (if isolated DB needed)

```bash
# Update API env to point to the test database
ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP} "
  sed -i 's|/{MONGODB_DEFAULT_DB}|/<database>|' ~/.env.production
  docker stop {API_CONTAINER_NAME}; docker rm {API_CONTAINER_NAME}
  docker run -d --name {API_CONTAINER_NAME} --restart unless-stopped -p 3000:3000 \
    --env-file ~/.env.production \
    {ECR_REGISTRY}/{ECR_PREFIX}/api:<tag>
"
```

The test user is auto-seeded by the API on startup if configured.

## Step 5b: Fix Workspace Gateway Config (if needed)

After workspaces boot, their gateway config may not include your QA frontend URL in
`gateway.controlUi.allowedOrigins`. Without this, the frontend WebSocket connection
is rejected with `origin not allowed`.

**Run on EVERY taken/pending workspace after deploy:**

```bash
# Get workspace IPs from controller
WORKSPACES=$(curl -sf {WORKSPACE_CONTROLLER_URL}/api/workspace/status | \
  python3 -c "import json,sys; d=json.load(sys.stdin); [print(ws['publicIp']) for s in ['pending','booting','taken'] for ws in d.get(s,[])]")

for IP in $WORKSPACES; do
  ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i {SSH_KEY_PATH} {SSH_USER_WORKSPACE}@$IP '
    # Update allowedOrigins to include your QA frontend URL
    # Update trustedProxies for nginx reverse proxy
    # Restart the gateway process
  '
done
```

Adapt the config update script to add `{APP_URL}` to `gateway.controlUi.allowedOrigins`
and set `gateway.trustedProxies` to trust your reverse proxy.

## Step 6: Verify Deployment

```bash
# Health checks — ALL must pass
curl -sf {API_URL}/health                          # → {"status":"ok"}
curl -sf -o /dev/null -w "%{http_code}" {APP_URL}  # → 200
curl -sf {WORKSPACE_CONTROLLER_URL}/health          # → {"status":"ok"}

# Verify correct code is deployed (check for PR-specific imports/routes)
ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP} 'docker exec {API_CONTAINER_NAME} head -10 /app/api/dist/src/routes/<changed-file>.js'

# Login test
curl -sf -X POST {API_URL}/auth/email/login \
  -H "Content-Type: application/json" -H "Origin: {APP_URL}" \
  -d '{"email":"{TEST_ACCOUNT_EMAIL}","password":"{TEST_ACCOUNT_PASSWORD}"}' | jq .success

# If agent branch changed, wait for workspace to boot
# Monitor: curl -sf {WORKSPACE_CONTROLLER_URL}/api/workspace/status | jq .
```

## Step 7: Report Deployment Status

Return to the calling skill:

```
✅ Deployed to QA environment:
- API: <branch> (<tag>)
- Frontend: <branch> (<tag>) with VITE_API_URL={API_URL}
- Agent: <branch> (via latest.txt)
- Database: <database>
- All health checks passing
```

## Rollback

To restore to main branch:

```bash
# Rebuild from main
git checkout main
# ... rebuild + deploy same as above with tag "latest"

# Reset agent to latest release
cd {AGENT_REPO_PATH}
VERSION=$(node -p "require('./package.json').version")
echo "$VERSION" | aws s3 cp - s3://{S3_AGENT_ASSETS_BUCKET}/cloud/latest.txt --profile {AWS_PROFILE}
```
