---
name: report-workflow
description: Workflow for reports and automations. When research or complex tasks are requested, produce an HTML report. When automation/cron is requested, ALWAYS create a sample report first for user approval before setting up the cron job.
metadata:
  emoji: 📋
  version: "1.0"
---

# Report Workflow Skill

## When to Create a Report

Create an HTML report (using `generate-report` skill) when the user asks you to:

- Research something online
- Analyze data or trends
- Compare options (agencies, tools, products, etc.)
- Pull data from multiple sources
- Any task where the output has structured findings

**Do NOT create a report for:**

- Simple questions ("what's the weather?", "what time is it?")
- Quick lookups with a one-line answer
- Conversational messages
- File operations or server tasks

## Automation / Cron Workflow

**When the user asks to set up any recurring automation that produces a report:**

### Step 1: Create a Sample Report

- Run the task ONCE immediately
- Generate the full HTML report using `generate-report` and `frontend-design` skills
- Send the HTML file to the user
- Ask: "Here's a sample — does this format work? Any changes before I set up the automation?"

### Step 2: Wait for Approval

- Do NOT create the cron job yet
- Wait for the user to approve or request changes
- If changes requested, regenerate and re-send

### Step 3: Set Up Automation

- Only after explicit approval, create the cron job
- The cron job prompt should replicate exactly what produced the approved sample
- Confirm the schedule with the user
- Send the cron job details (name, schedule, what it does)

## Key Rules

1. **Never skip the sample step** for recurring automations
2. **Always send the HTML file** when a report is generated
3. **Always use `generate-report` and `frontend-design` skills** for report creation
4. For one-off research tasks, create the report directly (no approval needed) — the approval flow is only for recurring/cron automations
