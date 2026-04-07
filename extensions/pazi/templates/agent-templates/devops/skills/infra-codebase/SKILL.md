---
name: infra-codebase
description: Map of the codebase — repos are cloned locally and can be read directly. Use when you need to find where code lives, trace a bug, or understand an implementation. Triggers on "where is the code for", "find in codebase", "which file", "source code", "implementation", "check the repo", "grep for".
---

# Codebase Navigator

Repos are cloned in the workspace. **Read files directly — don't guess.**

## Repo Locations

<!-- Updated during onboarding when repos are cloned -->

```
~/.openclaw/workspace/<repo-name>/     — description
```

_Not yet configured. Connect a code repository during onboarding._

## Project Structure

<!-- High-level map of each repo — key directories and what they contain -->

### Repo: _example_

| Path       | What                     |
| ---------- | ------------------------ |
| `src/`     | Main application source  |
| `config/`  | Configuration files      |
| `scripts/` | Build and deploy scripts |
| `docs/`    | Documentation            |

## Key Files

<!-- The most important files an engineer should know about -->

| File            | Purpose                   |
| --------------- | ------------------------- |
| _src/index.ts_  | _Application entry point_ |
| _src/config.ts_ | _Configuration loader_    |

## Quick Search

```bash
# Find where something is implemented
grep -rn "term" <repo>/src/ --include="*.ts" | head -20

# Recent changes
cd <repo> && git log --oneline -10

# Find all TODOs
grep -rn "TODO\|FIXME\|HACK" <repo>/src/ --include="*.ts"
```

## Reference Files

- `references/services.md` — Service-by-service code map (entry points, routes, key modules)
