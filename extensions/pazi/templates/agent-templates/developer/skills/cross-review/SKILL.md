---
name: cross-review
description: Run a cross-review between Codex (OpenAI) and Claude Code (Anthropic) on any coding task. Use when the user asks to plan, review, or cross-review a feature using both AI agents — or says things like "have Codex and Claude review this", "cross-review this feature", "run the agent review workflow", or "plan this with both agents".
metadata: { "openclaw": { "emoji": "⚔️" } }
---

# Cross-Review Skill

Run two coding agents (Codex + Claude Code) through a structured plan-and-review workflow on a codebase task. Both agents work in the **same worktree** — one per repo.

## Prerequisites

- Feature directory exists at `{feature_dir}` with `plans/` subdirectory
- Worktrees exist: `{feature_dir}/<repo>/` (and optional secondary repo)
- Task description written to `{feature_dir}/plans/task.md`

## Workflow

1. **Round 1 — Independent plans**: Both agents explore the worktree and write implementation plans
2. **Round 2 — Revised plans**: Each agent reads the OTHER agent's R1 plan in a fresh conversation
3. **Best plan**: Read both R2 plans, merge the best ideas into a final implementation plan
4. **HTML report**: Build collapsible-section viewer

## Key Constraints

- **Claude Code MUST use `pty: true`** in exec
- **Codex needs a git repo** as working directory — worktrees satisfy this
- **Codex sometimes overwrites plan files with summary stubs** — always verify file size after completion
- **Run agents sequentially if RAM < 8GB** — parallel runs can OOM on 7.6GB
- **Timeout: 3600s (60 min)** per agent — Codex can spend 30+ min exploring before writing

## Round 1: Independent Plans

Launch both agents. Each explores the worktree and writes a **high-level** implementation plan.

### Plan Style: High-Level Architecture, Not Code

Plans should focus on:

- **Which files to create/modify** (file paths)
- **What each change does** at a conceptual level (e.g. "add a new API route for X", "extend the Y component to support Z")
- **Architecture decisions** (where to put new logic, how components connect, data flow)
- **Step-by-step implementation order** (what to build first, dependencies between steps)
- **Edge cases and risks** to watch for

Plans should **NOT** include:

- Full code snippets or diffs (minimal pseudocode is OK when it clarifies an ambiguous approach)
- Complete function signatures or type definitions (mention the concept, not the syntax)
- Copy-paste-ready implementation

The goal is a **roadmap** that a coding agent can follow — not a pre-written solution. Leave the actual implementation to the coding agent.

### Claude Code (R1)

```bash
FEATURE_DIR="$FEATURES_DIR/$FEATURE"
ANTHROPIC_API_KEY=$(get_credential service=anthropic)  # Or read from your .env

cd "$FEATURE_DIR/$REPO_NAME" && \
ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
claude -p \
  --dangerously-skip-permissions \
  --model claude-opus-4-6 \
  --output-format stream-json --verbose \
  "Read the task at $FEATURE_DIR/plans/task.md.
Explore the codebase here: $FEATURE_DIR/$REPO_NAME
(and secondary repo if applicable: $FEATURE_DIR/$SECONDARY_REPO_NAME)

Create a HIGH-LEVEL implementation plan. Focus on:
- Which files to create or modify (file paths)
- What each change does conceptually (not code)
- Architecture decisions and data flow
- Step-by-step implementation order
- Edge cases and risks

Do NOT write code snippets, full function signatures, or type definitions.
Minimal pseudocode is OK only when it clarifies an ambiguous approach.
The goal is an architectural roadmap, not a pre-written solution.

Save your implementation plan to $FEATURE_DIR/plans/claude-plan-v1.md" \
  > "$FEATURE_DIR/$REPO_NAME/claude-r1-output.json" 2>&1
```

### Codex (R1)

```bash
FEATURE_DIR="$FEATURES_DIR/$FEATURE"

cd "$FEATURE_DIR/$REPO_NAME" && \
codex exec \
  --model gpt-5.3-codex \
  --dangerously-bypass-approvals-and-sandbox \
  "Read the task at $FEATURE_DIR/plans/task.md.
Explore the codebase here: $FEATURE_DIR/$REPO_NAME
(and secondary repo if applicable: $FEATURE_DIR/$SECONDARY_REPO_NAME)

Create a HIGH-LEVEL implementation plan. Focus on:
- Which files to create or modify (file paths)
- What each change does conceptually (not code)
- Architecture decisions and data flow
- Step-by-step implementation order
- Edge cases and risks

Do NOT write code snippets, full function signatures, or type definitions.
Minimal pseudocode is OK only when it clarifies an ambiguous approach.
The goal is an architectural roadmap, not a pre-written solution.

Save your implementation plan to $FEATURE_DIR/plans/codex-plan-v1.md" \
  > "$FEATURE_DIR/$REPO_NAME/codex-r1-output.txt" 2>&1
```

**Execution:** Use `exec` with `pty: true`, `background: true`, timeout **3600 seconds**.

### Validation

After each agent exits, check plan file size:

- `wc -c < {feature_dir}/plans/{agent}-plan-v1.md` — must be >500 bytes
- If too small or missing: check the output log, kill stuck process, relaunch with same prompt
- **Never skip a round** — all 4 rounds must complete successfully

## Round 2: Revised Plans (Cross-Pollinated)

Fresh conversations. Each agent reads the OTHER agent's R1 plan and creates a new plan.

### Claude Code (R2)

```bash
FEATURE_DIR="$FEATURES_DIR/$FEATURE"
ANTHROPIC_API_KEY=$(get_credential service=anthropic)  # Or read from your .env

cd "$FEATURE_DIR/$REPO_NAME" && \
ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
claude -p \
  --dangerously-skip-permissions \
  --model claude-opus-4-6 \
  --output-format stream-json --verbose \
  "You are tasked with planning a feature.

Read the task description: $FEATURE_DIR/plans/task.md

Another AI agent (Codex) has already created a plan for this task.
Read their plan here: $FEATURE_DIR/plans/codex-plan-v1.md

Now explore the codebase yourself:
- Main repo: $FEATURE_DIR/$REPO_NAME/
- Secondary repo (if applicable): $FEATURE_DIR/$SECONDARY_REPO_NAME/

Create YOUR OWN high-level implementation plan, incorporating good ideas
from Codex's plan where appropriate. Where you disagree, explain why.

Focus on:
- Which files to create or modify (file paths)
- What each change does conceptually (not code)
- Architecture decisions and data flow
- Step-by-step implementation order
- Edge cases and risks

Do NOT write code snippets, full function signatures, or type definitions.
Minimal pseudocode is OK only when it clarifies an ambiguous approach.
The goal is an architectural roadmap, not a pre-written solution.

Save your plan to $FEATURE_DIR/plans/claude-plan-v2.md" \
  > "$FEATURE_DIR/$REPO_NAME/claude-r2-output.json" 2>&1
```

### Codex (R2)

```bash
FEATURE_DIR="$FEATURES_DIR/$FEATURE"

cd "$FEATURE_DIR/$REPO_NAME" && \
codex exec \
  --model gpt-5.3-codex \
  --dangerously-bypass-approvals-and-sandbox \
  "You are tasked with planning a feature.

Read the task description: $FEATURE_DIR/plans/task.md

Another AI agent (Claude Code) has already created a plan for this task.
Read their plan here: $FEATURE_DIR/plans/claude-plan-v1.md

Now explore the codebase yourself:
- Main repo: $FEATURE_DIR/$REPO_NAME/
- Secondary repo (if applicable): $FEATURE_DIR/$SECONDARY_REPO_NAME/

Create YOUR OWN high-level implementation plan, incorporating good ideas
from Claude Code's plan where appropriate. Where you disagree, explain why.

Focus on:
- Which files to create or modify (file paths)
- What each change does conceptually (not code)
- Architecture decisions and data flow
- Step-by-step implementation order
- Edge cases and risks

Do NOT write code snippets, full function signatures, or type definitions.
Minimal pseudocode is OK only when it clarifies an ambiguous approach.
The goal is an architectural roadmap, not a pre-written solution.

Save your plan to $FEATURE_DIR/plans/codex-plan-v2.md" \
  > "$FEATURE_DIR/$REPO_NAME/codex-r2-output.txt" 2>&1
```

Same execution and validation rules as R1.

## Best Plan

Read both R2 plans. Write `{feature_dir}/plans/best-plan.md` — this IS the implementation roadmap that will be handed to the coding agent.

Write it as a **high-level architectural plan** by:

1. Taking the best ideas from both agents' R2 plans
2. Resolving any disagreements (pick the better approach, explain briefly why)
3. Producing a single, coherent plan with:
   - File paths to create or modify
   - What each change does at a conceptual level
   - Architecture decisions and data flow
   - Step-by-step implementation order
   - Edge cases and risks to watch for
4. **No code** — or minimal pseudocode only when it clarifies an ambiguous approach
5. Include a brief **scorecard** rating each agent (detail, architecture, minimalism, correctness, edge cases)

The coding agent will figure out the actual code. The plan's job is to tell it _what_ to build and _where_, not _how_ to write it line by line.

Also write `{feature_dir}/plans/verdict.md` with the scoring rationale.

## HTML Report

Build a dark-themed collapsible viewer with sections:

1. Task description
2. Round 1 plans (both agents)
3. Round 2 revised plans (both agents)
4. Best Plan (final implementation plan)

Use `marked.js` for markdown rendering. Save to `{feature_dir}/report.html`.

## Agent Output Logs

All agent output is saved to files in the worktree (cleaned up when feature directory is deleted):

- `{feature_dir}/$REPO_NAME/claude-r1-output.json`
- `{feature_dir}/$REPO_NAME/claude-r2-output.json`
- `{feature_dir}/$REPO_NAME/codex-r1-output.txt`
- `{feature_dir}/$REPO_NAME/codex-r2-output.txt`

## Troubleshooting

- **Codex file is 0 bytes after exit**: Check output log. Relaunch.
- **Codex overwrote plan with stub**: `wc -c` — if <1KB, check output log or relaunch.
- **Claude produces no output**: Verify `pty: true` was used.
- **Worktree creation fails**: Ensure branch name doesn't already exist (`git branch -D` first).
- **"fatal: '<path>' is already checked out"**: Each worktree needs a unique branch name.
