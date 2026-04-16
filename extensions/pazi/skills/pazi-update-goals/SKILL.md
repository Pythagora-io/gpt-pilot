---
name: pazi-update-goals
description: Track and maintain user goals. Use when a user reports progress on a goal, a goal needs to be edited, a goal-related cron check-in fires, or GOALS.md needs to be created or updated.
metadata: { "openclaw": { "emoji": "📈" } }
---

# Pazi Update Goals

## 1. GOALS.md — format and maintenance

File: `GOALS.md` in workspace root. This is the high-level snapshot — keep it concise. Update after any goal event (created, edited, completed). Create it if missing.

### If creating GOALS.md for the first time (skip if GOALS.md already exists)

- **CRITICAL: You MUST ask the user for the Mission. Never guess, infer, or auto-generate a Mission statement — stop and ask before writing anything.** Once a Mission exists, never change it unless the user specifically asks or their direction has very obviously shifted.
- Append the following to `AGENTS.md` in the workspace root (create the file if it doesn't exist). Only do this once — check whether the Goals section already exists in AGENTS.md before appending:

  ```markdown
  ## Goals

  GOALS.md is your north star — read it immediately at the start of every session.
  Use the Mission as your overarching guide. Treat Active Goals as day-to-day priorities:
  if a current task is plausibly relevant to an active goal, factor that goal in.
  If you need detailed history on a goal's progress, read GOALS-LOG.md.
  ```

### GOALS.md format

```markdown
# Goals

## Mission

<user's overarching objective — MUST be provided by the user>

## Active Goals

### <Title>

- **Progress:** <currentValue> / <targetValue> <metricLabel> · <status emoji>
- **Deadline:** <targetDate>
- **Description:** <description>
- **Log:** See [GOALS-LOG.md](GOALS-LOG.md#<title-slug>)

## Completed Goals

### <Title>

- **Completed:** <date>
- **Result:** <finalValue> / <targetValue> <metricLabel>
- **Log:** See [GOALS-LOG.md](GOALS-LOG.md#<title-slug>)
```

Status emoji: ✅ on track · ⚠️ at risk · 🔴 off track (calculate from current vs. required pace).

## 2. GOALS-LOG.md — activity log

File: `GOALS-LOG.md` in workspace root. This is the detailed running log. **Every activity related to a goal must be recorded here** — creation, check-ins, cron fires, progress updates, trajectory changes, completions, user edits. If something happened with a goal, it goes in this log.

```markdown
# Goals Activity Log

For current goal state, see [GOALS.md](GOALS.md).

## Active Goals

### <Title>

- <date> — Goal created. Starting value: <startingValue>
- <date> — Check-in completed. <brief outcome, e.g. on track / behind by X / user updated target>
- <date> — User updated trajectory: <what changed>

## Completed Goals

### <Title>

- <date> — Goal created. Starting value: <startingValue>
- <date> — <key milestone or check-in note>
- <date> — Goal completed. Final: <finalValue> / <targetValue>
```

When a goal is created, add a new section under Active Goals. When a goal is completed, add the final entry and move the goal's section to Completed Goals here AND move it to "Completed Goals" in GOALS.md.
