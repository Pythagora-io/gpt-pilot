#!/usr/bin/env bash
# =============================================================================
# Start OpenClaw Gateway for Pazi Dev Environment
# =============================================================================
# Usage:
#   ./dev-env/start-gateway.sh --port 13050 --token <gateway-token>
#   ./dev-env/start-gateway.sh --port 13050 --token <token> --anthropic-key <key>
#
# The gateway token MUST match the OPENCLAW_GATEWAY_TOKEN in the Pazi API .env.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

PORT=""
TOKEN=""
ANTHROPIC_KEY="${ANTHROPIC_API_KEY:-}"
ANTHROPIC_BASE="${ANTHROPIC_BASE_URL:-http://127.0.0.1:8765}"
PAZI_API="${PAZI_API_URL:-}"
SKIP_CHANNELS=1

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Required:
  --port PORT           Gateway port (must match API's OPENCLAW_GATEWAY_PORT)
  --token TOKEN         Gateway token (must match API's OPENCLAW_GATEWAY_TOKEN)

Optional:
  --anthropic-key KEY   Anthropic API key (default: \$ANTHROPIC_API_KEY)
  --anthropic-base URL  Anthropic base URL (default: http://127.0.0.1:8765)
  --pazi-api URL        Pazi API URL (default: auto-detect)
  --with-channels       Start with channel integrations (Slack, etc.)
  -h, --help            Show this help
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)           PORT="$2"; shift 2 ;;
        --token)          TOKEN="$2"; shift 2 ;;
        --anthropic-key)  ANTHROPIC_KEY="$2"; shift 2 ;;
        --anthropic-base) ANTHROPIC_BASE="$2"; shift 2 ;;
        --pazi-api)       PAZI_API="$2"; shift 2 ;;
        --with-channels)  SKIP_CHANNELS=0; shift ;;
        -h|--help)        usage ;;
        *)                echo "Unknown option: $1"; usage ;;
    esac
done

if [[ -z "$PORT" || -z "$TOKEN" ]]; then
    echo "Error: --port and --token are required."
    echo ""
    usage
fi

echo "Starting OpenClaw gateway..."
echo "  Port:     $PORT"
echo "  Token:    ${TOKEN:0:16}..."
echo "  Channels: $([ "$SKIP_CHANNELS" -eq 1 ] && echo "disabled" || echo "enabled")"
echo ""

cd "$REPO_ROOT"

export OPENCLAW_GATEWAY_PORT="$PORT"
export OPENCLAW_GATEWAY_TOKEN="$TOKEN"
export ANTHROPIC_BASE_URL="$ANTHROPIC_BASE"

if [[ -n "$ANTHROPIC_KEY" ]]; then
    export ANTHROPIC_API_KEY="$ANTHROPIC_KEY"
fi

if [[ -n "$PAZI_API" ]]; then
    export PAZI_API_URL="$PAZI_API"
fi

if [[ "$SKIP_CHANNELS" -eq 1 ]]; then
    export OPENCLAW_SKIP_CHANNELS=1
    export CLAWDBOT_SKIP_CHANNELS=1
fi

exec npm run gateway:dev
