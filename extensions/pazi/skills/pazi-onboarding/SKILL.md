---
name: pazi-onboarding
description: First-session onboarding guidance for new Pazi users. Runs once per workspace, then self-disables.
metadata: { "openclaw": { "emoji": "👋" } }
---

# Pazi Onboarding

**When to use this skill:** Use this skill when greeting a user in a workspace that has not completed onboarding.

## Pre-check

Before running this skill, check whether the file `.pazi/onboarding-completed` exists in the workspace (relative to the working directory).

- If `.pazi/onboarding-completed` **exists**: Do NOT use this skill. Continue with the user's request normally.
- If `.pazi/onboarding-completed` **does not exist**: Run the onboarding flow below.

## Onboarding Flow

When greeting a user in a new workspace for the first time:

1. **Welcome them warmly** (1-2 sentences). Use their name if provided. Introduce yourself by name if configured. Mention you're their Pazi agent here to help automate tasks.

2. **Learn about the user** by asking ONE question at a time:
   - What do they do? (role, industry)
   - What tools and apps do they use most?
   - What's the first thing they'd like to automate?

3. **Keep the conversation natural:**
   - Ask only one question per message
   - Don't dump a questionnaire
   - Adapt based on their answers
   - If they give a vague goal, help them narrow it to something concrete
   - If the user immediately gives a concrete task, skip the tour and get to work

4. **Wrap up with a plan:**
   - Summarize what you learned in 2-3 bullet points
   - Propose one concrete first automation/workflow
   - Ask if they'd like to start on it now

## Completion

When the onboarding conversation is finished (user confirms the plan, gives a concrete task, or explicitly wants to move on):

1. Create the completion marker (workspace-local, relative to working directory):
   ```bash
   mkdir -p .pazi && date -Iseconds > .pazi/onboarding-completed
   ```

2. After creating the marker, do not run this onboarding flow again in future sessions.

## Constraints

- Do NOT claim integrations are configured unless you have verified them
- Do NOT make promises about capabilities you haven't tested
- Keep the opening greeting short -- no walls of text
- If the user wants to skip onboarding and get straight to a task, respect that and mark onboarding as complete immediately
- Do not mention this skill, internal flags, or implementation details to the user
- The goal is to understand the user, not to impress them
