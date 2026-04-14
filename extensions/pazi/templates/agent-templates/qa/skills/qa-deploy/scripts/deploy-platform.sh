#!/bin/bash
# Deploy a platform service (api/frontend/workspace-controller) from a specific branch
# Usage: ./deploy-platform.sh <service> <branch> [database_name]
# Example: ./deploy-platform.sh api feature/voice-transcription qa_pr_501
#          ./deploy-platform.sh frontend feature/voice-transcription
#          ./deploy-platform.sh workspace-controller main
#
# CONFIGURATION: Set these environment variables before running, or edit the defaults below.
# All values must match your environment.md configuration.

set -euo pipefail

SERVICE="${1:?Usage: $0 <api|frontend|workspace-controller> <branch> [database_name]}"
BRANCH="${2:?Usage: $0 <service> <branch> [database_name]}"
DB_NAME="${3:-${MONGODB_DEFAULT_DB:-myDB}}"

# === CONFIGURE THESE FOR YOUR ENVIRONMENT ===
REPO_DIR="${PLATFORM_REPO_PATH:-/home/user/my-platform}"
ECR="${ECR_REGISTRY:-123456789012.dkr.ecr.us-east-1.amazonaws.com}"
PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-us-east-1}"
SSH_KEY="${SSH_KEY_PATH:-$HOME/.ssh/my-qa-key.pem}"

# Instance IPs — set via environment variables or edit defaults
declare -A IPS=(
  [api]="${API_EC2_IP:-10.0.1.100}"
  [frontend]="${FRONTEND_EC2_IP:-10.0.1.101}"
  [workspace-controller]="${WS_CONTROLLER_EC2_IP:-10.0.1.102}"
)

# Container names
declare -A CONTAINERS=(
  [api]="${API_CONTAINER_NAME:-my-api-production}"
  [frontend]="${FRONTEND_CONTAINER_NAME:-my-frontend-production}"
  [workspace-controller]="${WS_CONTROLLER_CONTAINER_NAME:-my-wsc-production}"
)

# ECR repos
ECR_PREFIX="${ECR_PREFIX:-qa}"
declare -A REPOS=(
  [api]="${ECR_PREFIX}/api"
  [frontend]="${ECR_PREFIX}/frontend"
  [workspace-controller]="${ECR_PREFIX}/workspace-controller"
)

# Dockerfiles — frontend uses custom QA Dockerfile with VITE build args
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_QA_DOCKERFILE="${SCRIPT_DIR}/Dockerfile.frontend-qa"

declare -A DOCKERFILES=(
  [api]="api/Dockerfile"
  [frontend]="$FRONTEND_QA_DOCKERFILE"
  [workspace-controller]="workspace-controller/Dockerfile"
)

# Frontend build args — set via environment variables
VITE_API_URL="${API_URL:-https://api.qa.example.com}"
VITE_WEB_APP_URL="${APP_URL:-https://qa.example.com}"

IP="${IPS[$SERVICE]}"
CONTAINER="${CONTAINERS[$SERVICE]}"
REPO="${REPOS[$SERVICE]}"
DOCKERFILE="${DOCKERFILES[$SERVICE]}"
TAG="branch-$(echo $BRANCH | tr '/' '-')"

echo "=== Deploying $SERVICE from branch $BRANCH ==="
echo "Image: $ECR/$REPO:$TAG"
echo "Target: $IP ($CONTAINER)"

# 1. Find source code — check worktrees first, fall back to checkout
cd "$REPO_DIR"
ORIGINAL_BRANCH=$(git branch --show-current)
WORKTREE_PATH=$(git worktree list | grep "$BRANCH" | awk '{print $1}' | head -1)

if [ -n "$WORKTREE_PATH" ] && [ -d "$WORKTREE_PATH" ]; then
  echo "Using existing worktree at $WORKTREE_PATH"
  cd "$WORKTREE_PATH"
else
  echo "Checking out $BRANCH..."
  git fetch origin "$BRANCH"
  git checkout "$BRANCH"
fi

# 2. Build image (--no-cache to avoid stale layers from previous branches)
echo "Building Docker image (--no-cache)..."
if [ "$SERVICE" = "frontend" ]; then
  if [ ! -f "$FRONTEND_QA_DOCKERFILE" ]; then
    echo "ERROR: Frontend QA Dockerfile not found at $FRONTEND_QA_DOCKERFILE"
    exit 1
  fi
  docker build --no-cache \
    --build-arg BUILD_MODE=production \
    --build-arg VITE_API_URL="$VITE_API_URL" \
    --build-arg VITE_WEB_APP_URL="$VITE_WEB_APP_URL" \
    -t "$ECR/$REPO:$TAG" -f "$FRONTEND_QA_DOCKERFILE" .
else
  docker build --no-cache -t "$ECR/$REPO:$TAG" -f "$DOCKERFILE" .
fi

# 3. Push to ECR
echo "Pushing to ECR..."
aws ecr get-login-password --region "$REGION" --profile "$PROFILE" | docker login --username AWS --password-stdin "$ECR" 2>/dev/null
docker push "$ECR/$REPO:$TAG"

# 4. Update database name in API env if specified
if [ "$SERVICE" = "api" ] && [ "$DB_NAME" != "${MONGODB_DEFAULT_DB:-myDB}" ]; then
  echo "Updating MongoDB database to $DB_NAME..."
  SSH_USER="${SSH_USER_EC2:-ec2-user}"
  ssh -i "$SSH_KEY" "$SSH_USER"@"$IP" "sed -i 's|/${MONGODB_DEFAULT_DB:-myDB}|/$DB_NAME|' ~/.env.production"
fi

# 5. Deploy on EC2
echo "Deploying on EC2..."
SSH_USER="${SSH_USER_EC2:-ec2-user}"
ssh -i "$SSH_KEY" "$SSH_USER"@"$IP" "
  aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR 2>/dev/null
  docker pull $ECR/$REPO:$TAG
  docker stop $CONTAINER 2>/dev/null || true
  docker rm $CONTAINER 2>/dev/null || true
  docker run -d --name $CONTAINER --restart unless-stopped -p 3000:3000 \
    $([ -f ~/.env.production ] && echo '--env-file ~/.env.production') \
    $ECR/$REPO:$TAG
  sleep 5
  curl -sf http://localhost:3000/health || curl -sf -o /dev/null -w 'HTTP %{http_code}' http://localhost:3000/
"

# 6. Restore original branch (only if we checked out, not if worktree)
if [ -z "$WORKTREE_PATH" ]; then
  cd "$REPO_DIR"
  git checkout "$ORIGINAL_BRANCH" 2>/dev/null || true
fi

echo ""
echo "✅ $SERVICE deployed from $BRANCH"
