---
name: pazi-update-goals
description: Track and maintain user goals. Use when a user reports progress on a goal, a goal needs to be edited, a goal-related cron check-in fires, or GOALS.md needs to be created or updated.
metadata: { "openclaw": { "emoji": "📈" } }
---

# Pazi Update Goals

## a. GOALS.md — format and maintenance

File: `GOALS.md` in workspace root. Update after any goal event (created, updated, completed). Create it if missing — ask the user for Mission text once; only revisit if their direction has clearly shifted.

```markdown
# Goals

## Mission

<user's overarching objective — ask once, update only if direction clearly shifts>

## Active Goals

### <Title>

- **Progress:** <currentValue> / <targetValue> <metricLabel> · <status emoji>
- **Deadline:** <targetDate>
- **Description:** <description>

**Activity log:**

- <date> — Goal created. Starting value: <startingValue>
- <date> — Check-in completed. <brief outcome, e.g. on track / behind by X / user updated target>
- <date> — User updated trajectory: <what changed>

## Completed Goals

### <Title>

- **Completed:** <date>
- **Result:** <finalValue> / <targetValue> <metricLabel>

**Activity log:**

- <date> — Goal created
- <date> — <key milestone or check-in note>
- <date> — Goal achieved
```

Status emoji: ✅ on track · ⚠️ at risk · 🔴 off track (calculate from current vs. required pace).

**First-time GOALS.md creation — also update AGENTS.md:**
When creating GOALS.md for the first time, append the following to `AGENTS.md` in the workspace root (create the file if it doesn't exist):

```markdown
## Goals

GOALS.md is your north star — read it immediately at the start of every session.
Use the Mission as your overarching guide. Treat Active Goals as day-to-day priorities:
if a current task is plausibly relevant to an active goal, factor that goal in.
```

Only do this once — check whether the Goals section already exists in AGENTS.md before appending.

## b. When a goal cron fires

Follow the cron message instructions. When done, append to the goal's activity log in GOALS.md using the format in §a.
