---
name: phase-2-planning
description: "Phase 2 — Run cross-review planning with Codex + Claude Code, produce best plan, upload to S3, notify user."
---

# Phase 2: Planning (Cross-Review)

Run the cross-review to produce implementation plans, upload them to S3, and notify the user.

## Prerequisites

- Dev environment is running and verified (Phase 1)
- Feature directory exists at `{feature_dir}` with `plans/` subdirectory
- Worktrees exist: `{feature_dir}/<repo>/` (and optional secondary repo)

## Steps

### 2.1 Write Task Description

Create `{feature_dir}/plans/task.md` with:

- The original Linear ticket title and description
- Any additional context from the user
- Constraints, requirements, or design references
- **Figma design URLs** — if the ticket references Figma designs, include the full Figma URLs (e.g. `https://www.figma.com/design/<FILE_KEY>/<name>?node-id=<NODE_ID>`). Both Codex and Claude Code have `figma-mcp` configured and can inspect designs directly during planning.

### 2.2 Run Cross-Review

Both agents have access to Figma designs via the `figma-mcp` MCP server. When a Figma URL is included in `task.md`, agents can:

- Add the file context with `add_figma_file`
- Inspect specific nodes/frames with `view_node`
- Read design comments with `read_comments`

This means agents can reference actual design details (layout, components, spacing, text content) in their implementation plans rather than relying solely on text descriptions.

Read and follow the `cross-review` skill. This produces:

- `{feature_dir}/plans/claude-plan-v1.md` — Claude Round 1
- `{feature_dir}/plans/codex-plan-v1.md` — Codex Round 1
- `{feature_dir}/plans/claude-plan-v2.md` — Claude Round 2 (cross-pollinated)
- `{feature_dir}/plans/codex-plan-v2.md` — Codex Round 2 (cross-pollinated)
- `{feature_dir}/plans/best-plan.md` — The merged best plan
- `{feature_dir}/plans/verdict.md` — Verdict with scoring
- `{feature_dir}/report.html` — HTML report

### 2.3 Upload Plans to S3

```bash
TICKET_ID="{TICKET_ID}"
FEATURE_DIR="{feature_dir}"
S3_BUCKET="$S3_BUCKET"  # Set during build-developer-agent setup
S3_PREFIX="plans/$TICKET_ID"

for f in "$FEATURE_DIR/plans/"*.md; do
  aws s3 cp "$f" "s3://$S3_BUCKET/$S3_PREFIX/$(basename $f)" --content-type "text/markdown"
done

aws s3 cp "$FEATURE_DIR/report.html" "s3://$S3_BUCKET/$S3_PREFIX/report.html" --content-type "text/html"
```

### 2.4 Comment on Linear Ticket

```
📋 Cross-review complete!

**Best plan:** {winner agent}'s approach (score: {X}/10)
**Key decisions:** {1-2 sentence summary}

📄 Plans:
- [Best Plan]($S3_PUBLIC_URL/plans/{TICKET_ID}/best-plan.md)
- [Full Report]($S3_PUBLIC_URL/plans/{TICKET_ID}/report.html)
- [Codex Plan v2]($S3_PUBLIC_URL/plans/{TICKET_ID}/codex-plan-v2.md)
- [Claude Plan v2]($S3_PUBLIC_URL/plans/{TICKET_ID}/claude-plan-v2.md)

Auto-proceeding to implementation.
```

### 2.5 Send Report to User

Send the report to the user via `sessions_send` to the parent session (see AGENTS.md ⚠️ Messaging section — NEVER use `message` tool directly):

```
📊 Cross-review complete for {TICKET_ID}!

🏆 Winner: {agent} (score: {X}/10)
📝 Key decisions: {brief summary of approach}
📄 Files affected: ~{N} files
🔗 Full report: $S3_PUBLIC_URL/plans/{TICKET_ID}/report.html

Auto-proceeding to implementation.
```

### 2.6 Credential Check

Before proceeding to implementation, review the best plan and ask yourself:

- Does this feature require any new API keys, secrets, or third-party credentials that we don't already have?
- Are there any services (Stripe, OAuth providers, external APIs, etc.) that need new or updated credentials?

If yes:

1. **Ask the user** (via parent session or chat) for the specific credentials needed
2. **Explain what they're for** — e.g. "I need a Twilio API key for SMS verification — the plan requires sending OTP codes"
3. **Wait for them to provide the credentials** before moving to Phase 3
4. Store any new credentials via `save_credential` for future use

If no new credentials are needed, proceed directly.

> **During implementation (Phase 3):** If you discover you're blocked because of missing credentials that weren't obvious during planning, **stop and ask immediately** rather than trying to work around it.

### 2.7 Update Checklist

Mark all Phase 2 items as checked in `{feature_dir}/checklist.md`.

## Phase Complete

Post the phase transition update (see AGENTS.md), then read skill: `phase-3-implementation`
