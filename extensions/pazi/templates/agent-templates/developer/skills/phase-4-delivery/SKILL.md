---
name: phase-4-delivery
description: "Phase 4 — Create PR with full template, run independent Codex review, fix-review loop, send final message."
---

# Phase 4: Delivery

Create the PR, run an independent Codex review, and deliver the final results to the user.

## Prerequisites

- Code is committed in the worktree (Phase 3)

## Steps

### 4.1 Create PR with Full Template

Push the branch and create the PR.

```bash
FEATURE_DIR="$FEATURES_DIR/$FEATURE"
cd "$FEATURE_DIR/$REPO_NAME"
BRANCH=$(git branch --show-current)

git push https://${GITHUB_TOKEN}@github.com/<OWNER>/<REPO>.git "$BRANCH"
```

#### PR Body Template (MANDATORY)

Every PR MUST use this template. Fill in all sections.

```markdown
## 🔗 Links

- **Cross-review report:** $S3_PUBLIC_URL/plans/{TICKET_ID}/report.html
- **Linear ticket:** https://linear.app/<WORKSPACE>/issue/{TICKET_ID}

## 📋 User Request

{contents of task.md — the original ticket description}

## 🏗️ What Was Implemented

{summary of changes, architectural decisions, deviations from plan}

### Files Changed
```

{git diff staging..HEAD --stat}

```

### Commits
```

{git log staging..HEAD --oneline}

```

## 📊 Cross-Review Summary
- **Winner:** {agent} (score: {X}/10)
- **Key decisions:** {brief summary}
- **Full report:** [View cross-review report]($S3_PUBLIC_URL/plans/{TICKET_ID}/report.html)

## 📝 Additional Details
{edge cases handled, known limitations, dependencies, migration notes}
```

Create via GitHub API:

```python
import json, urllib.request

body = json.dumps({
    'title': 'feat: {FEATURE_TITLE}',
    'body': PR_BODY,
    'head': BRANCH,
    'base': 'staging',
    'draft': False
})
req = urllib.request.Request(
    'https://api.github.com/repos/<OWNER>/<REPO>/pulls',
    data=body.encode(),
    headers={
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github.v3+json'
    },
    method='POST'
)
resp = urllib.request.urlopen(req)
d = json.loads(resp.read())
print(f'PR #{d["number"]}: {d["html_url"]}')
```

**Always create PRs as ready for review** — no drafts. Do the same for the agent repo if applicable.

### 4.2 Independent Codex PR Review

Spawn Codex in a clean temp directory. It gets NO implementation context — only the diff, plan, and task.

```bash
REVIEW_DIR=$(mktemp -d /tmp/pr-review-XXXXXX)
cd "$REVIEW_DIR"
git clone --depth=50 "https://${GITHUB_TOKEN}@github.com/<OWNER>/<REPO>.git" repo
cd repo
git fetch origin "$BRANCH"
git checkout "$BRANCH"
DIFF=$(git diff "origin/staging...$BRANCH")
TASK=$(cat "{feature_dir}/plans/task.md")
PLAN=$(cat "{feature_dir}/plans/best-plan.md")
```

Launch Codex:

```bash
cd "$REVIEW_DIR/repo" && \
codex exec \
  --model gpt-5.3-codex \
  --dangerously-bypass-approvals-and-sandbox \
  "You are reviewing PR #$PR_NUMBER for this project.

Your job: review this pull request and decide whether it should be merged.

## Original User Request
$TASK

## Implementation Plan
$PLAN

## PR Diff
$DIFF

## Your Review

Analyze thoroughly:
1. Does the implementation match the plan and user request?
2. Any bugs, logic errors, or edge cases missed?
3. Code quality — naming, structure, patterns, consistency?
4. Security concerns (XSS, injection, auth)?
5. Performance concerns?
6. Missing error handling or validation?
7. Unnecessary or dead code?

Write a detailed review with file names and line numbers.
End with: ✅ APPROVE, 🔄 REQUEST CHANGES, or ❌ REJECT.

At the very end of your review, add a line: '🤖 Review performed by: gpt-5.3-codex'

Output ONLY the review text." \
  > "$REVIEW_DIR/codex-review-output.txt" 2>&1
```

- `exec` with `pty: true`, `background: true`
- Timeout: **3600 seconds** (60 min)
- Post review as PR comment with 🔍 prefix
- **MANDATORY:** The review comment must always state which model performed the review (e.g. "🤖 Review performed by: gpt-5.3-codex"). If Codex's output doesn't include it, append it yourself before posting.
- Copy output log: `cp "$REVIEW_DIR/codex-review-output.txt" "{feature_dir}/$REPO_NAME/codex-pr-review-output.txt"`
- Clean up: `rm -rf "$REVIEW_DIR"`

### 4.3 Automated Fix-Review Loop (MANDATORY)

After the review:

1. **APPROVE** → proceed to 4.4
2. **REQUEST CHANGES:**
   a. Extract issues from the review
   b. Launch Claude Code to fix:
   ```bash
   cd "$FEATURE_DIR/$REPO_NAME" && \
   ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
   claude -p \
     --dangerously-skip-permissions \
     --model claude-opus-4-6 \
     --output-format stream-json --verbose \
     "Fix these PR review issues: ..." \
     > "$FEATURE_DIR/$REPO_NAME/claude-pr-fix-r{N}-output.json" 2>&1
   ```
   c. Fix + commit + push
   d. Re-run Codex review (fresh diff)
   e. **Loop until APPROVE** (max 3 iterations)
   f. If still REQUEST CHANGES after 3 rounds → notify user with remaining issues
3. **REJECT** → notify user immediately

```
┌─────────────────────────────────────┐
│         PR Review Loop              │
│  1. Run independent review          │
│  2. Parse verdict                   │
│     ├─ APPROVE → deliver            │
│     ├─ REQUEST CHANGES:             │
│     │   a. Launch Claude Code fix   │
│     │   b. Fix + commit + push      │
│     │   c. Re-review (go to 1)      │
│     └─ REJECT → notify user         │
│  Max iterations: 3                  │
└─────────────────────────────────────┘
```

### 4.4 Send Final Message to User

Send via `sessions_send` to parent session (NEVER use `message` tool directly — see AGENTS.md ⚠️ Messaging):

```
✅ Feature "{feature_name}" is done!

📝 PR: https://github.com/<OWNER>/<REPO>/pull/{N}
📊 Cross-review: $S3_PUBLIC_URL/plans/{TICKET_ID}/report.html

Changes: {N} files, +{added} -{removed} lines
Tests: {N} passing, 0 failing
```

### 4.5 Update Linear Ticket

- Move to the appropriate "QA" or "Review" state (use state IDs from your Linear workspace)
- Assign to the QA person if applicable
- Comment: "✅ Implementation complete! PR #{N} created. Ready for review/QA."

### 4.6 Notify Reviewer / QA

After the Linear ticket is updated, notify the relevant person or team that the PR is ready for review. This can be done via Slack, Linear comment, or whatever communication channel is set up.

### 4.7 Update Checklist

Mark all Phase 4 items as checked in `{feature_dir}/checklist.md`.

## Agent Output Logs

All output saved in the worktree (cleaned up when feature directory is deleted):

- `{feature_dir}/$REPO_NAME/codex-pr-review-output.txt`
- `{feature_dir}/$REPO_NAME/claude-pr-fix-r{N}-output.json` (if fix rounds were needed)

## Workflow Complete

The coder's job is done. The PR is delivered, the user is notified, and the Linear ticket is in "QA" assigned to the QA person.

Cleanup (worktree deletion) happens separately when the PR is merged or closed — that's the main agent's responsibility, not yours.
