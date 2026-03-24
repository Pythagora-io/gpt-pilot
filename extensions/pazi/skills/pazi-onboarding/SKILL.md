---
name: pazi-onboarding
description: Guide new users through their first experience with Pazi -- help them understand the platform, build their first agents, and get excited about what's possible. Use when a user is new to Pazi, asks how to get started, wants to build their first agent, or needs help understanding what agents can do. Also use when suggesting agent ideas or walking through use cases.
metadata: { "openclaw": { "emoji": "👋" } }
---

# Pazi Onboarding

**When to use this skill:** Use this skill when greeting a user in a workspace that has not completed onboarding, or when a user asks what Pazi can do.

## Pre-check

Before running this skill, check whether the file `.pazi/onboarding-completed` exists in the workspace (relative to the working directory).

- If `.pazi/onboarding-completed` **exists**: Do NOT run the full onboarding flow. You can still reference agent ideas from `references/agent-ideas.md` if the user asks what to build.
- If `.pazi/onboarding-completed` **does not exist**: Run the onboarding flow below.

## Context

Your name and the user's name are already set in IDENTITY.md and USER.md. Read them and use them from the start. Do not ask "who are you?" or "what should I call you?" -- you already know.

## Onboarding Flow

1. **Say hello** (1-2 sentences). Use their name. Introduce yourself by name. Keep it casual. Then ask what they do.

2. **Learn about them** by asking ONE question at a time:
   - What do they do? (role, industry)
   - What tools and apps do they use most?
   - What takes up too much of their time?

3. **Keep it natural:**
   - One question per message
   - No questionnaires
   - Adapt based on their answers
   - If they give a concrete task early, skip the tour and get to work

4. **Suggest what to build** based on what you learned. Be specific. Reference ideas from `references/agent-ideas.md` but tailor them to what the user actually said.

5. **Wrap up:**
   - Summarize what you learned (2-3 bullet points)
   - Propose one concrete first task or automation
   - Ask if they want to start now

## After onboarding

Update workspace files with what you learned:

- `USER.md` -- role, tools, preferences
- `SOUL.md` -- adjust if they gave personality preferences
- `MEMORY.md` -- key context from the conversation

## Completion

When onboarding is done (user confirms the plan, gives a concrete task, or wants to move on):

```bash
mkdir -p .pazi && date -Iseconds > .pazi/onboarding-completed
```

## For deeper questions

- Platform docs: https://pazi.ai/docs
- OpenClaw docs: https://docs.openclaw.ai/

## Constraints

- Do NOT claim integrations are configured unless verified
- Do NOT make promises about capabilities you haven't tested
- Keep greetings short -- no walls of text
- If the user wants to skip onboarding, respect that and mark complete immediately
- Do not mention this skill, internal flags, or implementation details to the user
- The goal is to understand the user, not to impress them
