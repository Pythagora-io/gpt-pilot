---
name: environment-setup
description: Set up git worktrees for parallel feature development. Use when creating new feature worktrees, setting up dev environments for parallel features, or when told to work on a new feature in a separate worktree.
metadata: { "openclaw": { "emoji": "🌳" } }
---

# Worktree Setup Skill

Create isolated git worktrees for parallel feature development.

## Quick Reference

```bash
# Create a new feature worktree
local-worktree create <FEATURE>

# See all worktrees and their status
local-worktree status

# Teardown everything
local-worktree destroy <FEATURE>
```

## What `create` Does

1. Saves feature to `$FEATURES_DIR/port-assignments.json` (registry)
2. **Pulls latest changes** — fetches and pulls the base branch on both primary and secondary repos
3. Creates git worktrees from the base branch
4. Runs `npm install` + `npx husky` (sets up pre-commit hooks: lint-staged + typecheck) + builds shared packages

Result: feature worktrees ready at `$FEATURES_DIR/<FEATURE>/<repo>/`

## What `destroy` Does

1. Removes git worktrees + deletes feature branches
2. Cleans up registry (`port-assignments.json`)
3. Removes feature directory

## Key Paths

| Path                                  | Purpose                                     |
| ------------------------------------- | ------------------------------------------- |
| `$FEATURES_DIR/`                      | All feature worktree directories            |
| `$FEATURES_DIR/port-assignments.json` | Feature registry                            |
| `$PRIMARY_REPO/api/.env`              | Base repo secrets (source for all features) |

## Husky Pre-Commit Hooks

Every worktree MUST have husky set up before any commits:

- Pre-commit hook runs: `lint-staged` (ESLint + Prettier) → `npm run typecheck`
- The create script already does `npx husky` after `npm install`
- If committing and the hook isn't running, run `npx husky` in the worktree root

## Script Location

| Script           | Source                   | Installed to                    |
| ---------------- | ------------------------ | ------------------------------- |
| `local-worktree` | `scripts/local-worktree` | `/usr/local/bin/local-worktree` |

### Install / Reinstall

```bash
SKILL_DIR="<this skill's directory>"
sudo cp "$SKILL_DIR/scripts/local-worktree" /usr/local/bin/local-worktree
sudo chmod +x /usr/local/bin/local-worktree
```

## Notes

- All PRs target `staging` — never `main` directly
- Secondary repo branches from the same base branch
- Worktrees are code-only — no local services by default
