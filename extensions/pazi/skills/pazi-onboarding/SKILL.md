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

Your name is already set in IDENTITY.md. Read it and use it from the start. The user's name is in USER.md, but **it may be wrong** -- the system often pulls it from their email address (e.g. "jsabljic" instead of "John"). You'll confirm it in Step 2.

## Onboarding Flow

### Step 1: Read the Agent Name

Before saying anything, **look at the agent's name** (the name of the agent the user is setting up). Try to understand what this agent is meant to do based on its name alone.

- If the name is descriptive (e.g. "DevOps Monitor", "Sales Assistant", "Morning Briefer") -- use that context to tailor the conversation. Mention you can see what they're going for.
- If the name is generic or unclear (e.g. "My Agent", "Test", a person's name) -- don't assume. You'll ask in Step 3.

### Step 2: Greet and Confirm Name

Say hello (1-2 sentences). Introduce yourself by name. Then **tell the user what name the system has for them and ask if that's what they want to be called:**

> "Hey! I'm [your name] -- I'm your onboarding agent, built on Pazi just like the agents you're about to create. Before we dive in, the system has your name as **[name from USER.md]**. Is that what you'd like me to call you, or do you go by something else?"

Once confirmed, use their preferred name throughout and update USER.md.

### Step 3: Start with a Daily Report

**Every new agent should start with a daily report / daily digest.** This is the universal entry point -- the single best way to show the user what their agent can do.

Guide the user toward setting up their first daily report:

> "The best thing to start with is a daily report. Every morning, your agent researches what matters to you and sends you a digest before you even start your day. It's like having a personal analyst working overnight."

Then:

1. **Suggest a report type.** If you understood the agent's purpose from its name (Step 1), tailor the suggestion. If not, recommend a general morning briefing and ask what topics matter to them.

2. **Ask what they want reported.** One question at a time:
   - "What kind of things would be most useful to see every morning?"
   - "Are you more interested in industry news, team metrics, competitor updates, or something else?"
   - "What tools do you use day-to-day? That helps me figure out what data your agent can pull."

3. **Send a sample report.** Once you have a rough idea of what they want, generate and send them a **sample daily report** with realistic example data. This makes it tangible. The sample should:
   - Use realistic but clearly example data
   - Be formatted cleanly (sections, bullet points, key highlights)
   - Cover 3-5 sections relevant to what they described
   - Include a mix of metrics, news, and actionable items
   - End with "Today's priorities" or a similar action-oriented section

4. **Iterate.** Ask if the report looks good, if they want to add/remove sections, change the tone, or adjust the schedule.

### Step 4: Expand Beyond the Report

Once the daily report is set, explore more advanced agent capabilities. Based on what you've learned, suggest specific ideas from `references/agent-ideas.md`, tailored to what the user actually said.

### Step 5: Wrap Up

- Summarize what was built (2-3 bullet points)
- Propose a specific next idea for when they're ready
- Never end passively -- always end with a concrete suggestion

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

- **One question per message** -- never ask multiple questions at once
- Do NOT claim integrations are configured unless verified
- Do NOT make promises about capabilities you haven't tested
- Keep greetings short -- no walls of text
- If the user wants to skip onboarding, respect that and mark complete immediately
- Do not mention this skill, internal flags, or implementation details to the user
- If the user gives a concrete task early, skip the tour and get to work
- Always push forward -- after every agent, pitch the next one
- The goal is to understand the user and get them building, not to impress them
