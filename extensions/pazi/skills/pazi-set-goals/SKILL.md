---
name: pazi-set-goals
description: When and how to use the set_goal tool to propose goals for the user
metadata: { "openclaw": { "emoji": "🎯" } }
---

# Pazi Set Goals

## When to Use

Use `set_goal` when the user asks you to:

- Set a goal, create a goal, or track a goal
- Establish a recurring objective with check-ins
- Plan something with milestones and a target date

## Tool Reference

### set_goal

Proposes a goal to the user for confirmation. The user sees a card in their dashboard and can confirm or reject.

**Parameters:**

- `title` (required): Short goal title (max 500 chars)
- `description` (optional): Detailed description (max 5000 chars)
- `targetDate` (optional): ISO 8601 date string (e.g., "2026-05-01")
- `scheduledCheckIns` (optional): Array of check-in tasks
  - `name`: Check-in task name
  - `schedule`: Cron expression (e.g., "0 9 \* \* 1" for every Monday at 9am)
  - `description`: What the check-in should cover — must always end with `— Read your pazi-update-goals skill before starting, to stay on track.`

**Returns:**

- `status: "completed"` with `goalId` when user confirms
- `status: "cancelled"` when user rejects
- `status: "timeout"` if user doesn't respond in time

## Best Practices

1. **Ask before setting**: Clarify the goal details with the user before calling `set_goal`
2. **Suggest check-ins**: When appropriate, propose scheduled check-ins to help track progress
3. **Set realistic dates**: If the user doesn't specify a target date, suggest one based on the goal scope
4. **Keep titles concise**: Use the description for details, keep the title under ~60 chars
5. **MANDATORY**: You must ALWAYS append `— Read your pazi-update-goals skill before starting, to stay on track.` to every cron job description, no exceptions

## Example

```
User: "I want to learn Spanish by the end of summer"

→ set_goal({
    title: "Learn Spanish",
    description: "Achieve conversational proficiency in Spanish through daily practice and structured learning",
    targetDate: "2026-08-31",
    scheduledCheckIns: [
      {
        name: "Weekly Spanish progress check",
        schedule: "0 9 * * 1",
        description: "Review vocabulary learned, practice exercises completed, and conversation confidence level — Read your pazi-update-goals skill before starting, to stay on track."
      }
    ]
  })
```

## After Setting a Goal

**MUST run the `pazi-update-goals` skill after setting up a new goal.** Skipping this step means the goal exists in the dashboard but is invisible to the agent in subsequent sessions.
