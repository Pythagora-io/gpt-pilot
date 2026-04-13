---
name: phase-1-dev-environment-setup
description: "Phase 1 — Set up worktree dev environment for feature development."
---

# Phase 1: Dev Environment Setup

Set up the git worktree and install dependencies.

**Before starting:** Read the **environment-setup** skill (`skills/environment-setup/SKILL.md`) for full CLI reference.

## Prerequisites

- Feature directory exists at `{feature_dir}` with `plans/` subdirectory
- Linear ticket is in "In Progress" state

## Steps

### 1.1 Create Worktree Environment

```bash
local-worktree create $FEATURE
```

If `local-worktree` is not on PATH, install it from the environment-setup skill's `scripts/` directory.

If the feature already exists from a prior attempt, destroy first: `local-worktree destroy $FEATURE`

### 1.2 Verify Setup

Confirm the worktrees are ready:

```bash
# Check worktrees exist
ls -la $FEATURES_DIR/$FEATURE/$REPO_NAME/

# Verify husky is set up (if project uses husky)
ls -la $FEATURES_DIR/$FEATURE/$REPO_NAME/.husky/

# Verify project built successfully
# (check for dist/, build/, or whatever the project outputs)

# Verify node_modules exist (for Node.js projects)
ls $FEATURES_DIR/$FEATURE/$REPO_NAME/node_modules/.package-lock.json
```

### 1.3 Post Status to Linear

Post a comment on the Linear ticket:

```
🌳 Dev environment ready!

Worktrees created from base branch.
Dependencies installed, pre-commit hooks active.
Moving to planning phase.
```

### 1.4 Update Checklist

Mark all Phase 1 items as checked in `{feature_dir}/checklist.md`.

## Phase Complete

Post the phase transition update, then read skill: `phase-2-planning`
