---
name: phase-3-implementation
description: "Phase 3 — Inject Claude Code skills, launch Claude Code to build the feature, verify results."
---

# Phase 3: Implementation

Launch Claude Code to build the feature. The dev environment is already set up and verified (Phase 1), and the cross-review plan is ready (Phase 2).

> **⚠️ Do NOT explore the codebase yourself.** Claude Code does its own exploration. Your job is to launch the agent and verify the results.

## Prerequisites

- Worktrees are set up with dependencies installed (Phase 1)
- `{feature_dir}/plans/best-plan.md` exists (from Phase 2)
- `{feature_dir}/plans/task.md` exists
- Credential check completed (Phase 2.6) — all required API keys/secrets are available

> **If you get blocked by missing credentials during implementation**, stop and ask the user immediately. Don't try to work around missing credentials.

## Steps

### 3.1 Inject Claude Code Skills

Copy bundled skills into the worktree so Claude Code loads them automatically:

```bash
FEATURE_DIR="$FEATURES_DIR/$FEATURE"
SKILLS_SRC="$WORKSPACE/skills/phase-3-implementation/references/claude-code-skills"
WORKTREE="$FEATURE_DIR/$REPO_NAME"

mkdir -p "$WORKTREE/.claude/skills/development"
cp "$SKILLS_SRC/development.md" "$WORKTREE/.claude/skills/development/SKILL.md"

# Configure MCP servers
mkdir -p "$WORKTREE/.claude"
cat > "$WORKTREE/.claude/mcp.json" << 'EOF'
{
  "mcpServers": {
    "figma": {
      "command": "npx",
      "args": ["figma-mcp"],
      "env": {
        "FIGMA_API_KEY": "<YOUR_FIGMA_API_KEY>"
      }
    }
  }
}
EOF
```

### 3.2 Write the Implementation Prompt

Combine into a single prompt for Claude Code:

1. **The task** from `{feature_dir}/plans/task.md`
2. **The best plan** from `{feature_dir}/plans/best-plan.md`
3. **Implementation constraints** (see section 3.3)

### 3.3 Implementation Constraints (MANDATORY — include in every prompt)

```
CRITICAL IMPLEMENTATION RULES:

1. COMPLETE IMPLEMENTATION: Implement EVERY feature described in the plan.
   Do not skip, stub, or leave TODOs. Every button must work. Every
   endpoint must be functional. Every UI element must render correctly.

2. NO BUGS: The final code must be bug-free. Test everything you build.
   If something doesn't work, fix it before moving on.

3. TEST-DRIVEN DEVELOPMENT (backend only):
   - Write tests for backend functions, API endpoints, and data logic
   - Do NOT write tests for frontend/React components
   - All tests MUST pass before you declare implementation complete
   - Run tests with the project's test command (e.g. `npm test`)

4. VERIFY YOUR WORK: After implementing, verify:
   - Run the TypeScript compiler: npx tsc --noEmit
   - Run ESLint: npx eslint . --ext .ts,.tsx
   - Check for obvious runtime errors in the code

5. HUSKY PRE-COMMIT HOOK: Before committing, ensure husky is active:
   - Run `npx husky` in the repo root if the hook isn't set up
   - The pre-commit hook runs lint-staged (ESLint + Prettier) then typecheck
   - NEVER use --no-verify to bypass the hook
   - If a commit goes through without lint/typecheck output, STOP and fix husky

6. DO NOT COMMIT UNTIL VERIFIED: Do NOT make any git commits until:
   - All code is fully implemented (no stubs, no TODOs)
   - Backend tests pass
   - TypeScript compiles cleanly (`npx tsc --noEmit`)
   Only AFTER all checks pass, make a single commit (or a few atomic ones).
   Use conventional commit format: feat:, fix:, test:, refactor:

7. DO NOT modify files outside the scope of this feature unless
   absolutely necessary (shared utilities are OK).

8. If you encounter a bug in existing code that blocks your feature,
   fix it and note it in your commit message.

9. AGENT REPO SCOPE: If the feature requires changes to a secondary repository,
   respect any scope constraints defined during setup. Ask before modifying
   files outside the designated scope.
```

### 3.4 Launch Claude Code

```bash
FEATURE_DIR="$FEATURES_DIR/$FEATURE"
ANTHROPIC_API_KEY=$(get_credential service=anthropic)  # Or read from your .env

cd "$FEATURE_DIR/$REPO_NAME" && \
ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
claude -p \
  --dangerously-skip-permissions \
  --model claude-opus-4-6 \
  --output-format stream-json --verbose \
  "$IMPLEMENTATION_PROMPT" \
  > "$FEATURE_DIR/$REPO_NAME/claude-implementation-output.json" 2>&1
```

**Execution:** `exec` with `pty: true`, `background: true`, timeout **3600 seconds** (60 min).

### 3.5 Post-Implementation Verification

After Claude Code exits:

1. **Check exit code** — 0 means clean, non-zero means investigate
2. **Review git log** — verify commits look sensible
3. **Check for leftover TODOs**: `grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.ts" --include="*.tsx" {feature_dir}/$REPO_NAME/`
4. **Run backend tests**: `cd {feature_dir}/$REPO_NAME && npm test 2>&1` (or the project's test command)
5. If tests fail, **relaunch Claude Code** with the failures:
   ```bash
   cd "$FEATURE_DIR/$REPO_NAME" && \
   ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
   claude -p \
     --dangerously-skip-permissions \
     --model claude-opus-4-6 \
     --output-format stream-json --verbose \
     "The following tests failed. Fix them: ..." \
     > "$FEATURE_DIR/$REPO_NAME/claude-bugfix-output.json" 2>&1
   ```

### 3.6 Comment on Linear Ticket

Post a progress update on the Linear ticket (via Pipedream `linear_app-create-comment`):

```
🛠️ Implementation complete!

**Commits:** {N} commits on branch `{BRANCH}`
**Files changed:** {N} files (+{added} -{removed})
**Tests:** {pass/fail summary}
**Status:** Code committed, moving to PR creation & review.
```

### 3.7 Update Checklist

Mark all Phase 3 items as checked in `{feature_dir}/checklist.md`.

## Agent Output Logs

All output saved in the worktree (cleaned up when feature directory is deleted):

- `{feature_dir}/$REPO_NAME/claude-implementation-output.json`
- `{feature_dir}/$REPO_NAME/claude-bugfix-output.json` (if bug fixes were needed)

## Phase Complete

Post the phase transition update (see AGENTS.md), then read skill: `phase-4-delivery`
