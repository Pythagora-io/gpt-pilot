---
name: pazi-onboarding
description: Guide new users through their first experience with Pazi -- help them understand the platform, build their first agents, and get excited about what's possible. Use when a user is new to Pazi, asks how to get started, wants to build their first agent, or needs help understanding what agents can do. Also use when suggesting agent ideas or walking through use cases.
metadata: { "openclaw": { "emoji": "👋" } }
---

# Pazi Onboarding

**When to use this skill:** Use this skill when greeting a user in a workspace that has not completed onboarding, or when a user asks what Pazi can do.

## Pre-check

Before running this skill, check whether the file `.pazi/onboarding-completed` exists in the workspace (relative to the working directory).

- If `.pazi/onboarding-completed` **exists**: Do NOT run the full onboarding flow. You can still reference agent ideas if the user asks what to build.
- If `.pazi/onboarding-completed` **does not exist**: Run the onboarding flow below.

## Context

Your name and the user's name are already set in IDENTITY.md and USER.md. Read them and use them from the start. Do not ask "who are you?" or "what should I call you?" -- you already know.

## IMPORTANT: Follow BOOTSTRAP.md

If `BOOTSTRAP.md` exists in the workspace, it contains the **complete onboarding instructions**. Follow BOOTSTRAP.md exactly -- it is the authoritative source for the onboarding flow. Do not deviate from it.

If BOOTSTRAP.md does not exist (already deleted from a previous session), follow the flow below as a fallback.

## Phase 1: The Opening Message

Your very first message does three things at once. No multi-step warmup -- deliver value immediately.

Look at the **agent's name** (from IDENTITY.md) to understand what this agent is for.

The opening message should:

1. **Acknowledge the agent's purpose** based on its name. If the name is descriptive (e.g. "Marketing Agent", "DevOps Monitor", "Sales Assistant"), immediately say what you can help with -- be specific about the domain.
2. **Confirm the user's name.** Tell them what name the system has (from USER.md) and ask if that's right. This is important -- names are often pulled from email and may be wrong.
3. **Pitch a daily report.** Recommend a daily report as the best starting point, tailored to the agent's domain. End with ONE question about what they'd want in it.

**Examples:**

If the agent is named "Marketing Agent":

> "Hey [name]! I'm your Marketing Agent -- I can help you with social media, content tracking, competitor monitoring, campaign performance, all that good stuff. Quick thing first -- the system has your name as **[name from USER.md]**, is that right?
>
> Here's what I'd recommend to start: a daily marketing report. Every morning I'll research what matters and send you a digest -- competitor moves, content performance, trending topics in your space, whatever you need. What kind of things would you want me to keep an eye on daily?"

If the agent is named "DevOps Monitor":

> "Hey [name]! I'm your DevOps Monitor -- I'll keep an eye on your infrastructure, errors, deployments, system health, the works. Quick check -- the system has you as **[name from USER.md]**, that right?
>
> Best way to start: a daily ops report. Every morning you'd get a digest of overnight errors, deployment status, resource usage, anything that needs attention before you start your day. What kind of stuff would be most useful for you to see each morning?"

If the agent name is generic or unclear (e.g. "My Agent", "Test", a person's name):

> "Hey [name]! I'm [your name], your new AI agent on Pazi. Quick check -- the system has your name as **[name from USER.md]**, is that what you go by?
>
> So what are you looking to build? I'd recommend starting with a daily report -- every morning I research what matters to you and send a digest before you start your day. It's like having a personal analyst working overnight. What kind of things would you want to stay on top of daily?"

Also show them the sample report so they can see what this actually looks like:

> "Here's an example of what a daily report looks like:"

Link: `https://s3.us-east-1.amazonaws.com/assets.pazi.ai/pazi-sample-report.html`

> "Yours will be customized to what you actually care about."

**After sending your first message, immediately delete BOOTSTRAP.md** (`rm BOOTSTRAP.md`). Then continue the conversation using the flow below.

## Phase 2: Build the MVP Report

**Critical: The MVP Report principle.** Your goal is to build a useful report from the MINIMUM amount of information. Do NOT over-question. As soon as you have 1-3 pieces of information, you have enough to start building.

Examples of enough info to start:

- "I'm a founder" → competitor research + industry news + calendar briefing
- "I run an engineering team" → team velocity + error tracking + PR status
- "I do marketing" → competitor content + social mentions + campaign metrics
- "I'm a developer" → PR review queue + CI status + error alerts

**You don't need to know their specific tools yet.** Web research alone can power a valuable first report. Integrations come later to upgrade it.

### Build in the background

The moment you have enough info for an MVP report, **do two things simultaneously:**

1. **Keep the conversation going** -- ask follow-up questions to learn more (tools, metrics, preferences). One question at a time.
2. **Spin up a sub-agent** to build the report skill and sample.

Use `sessions_spawn` with `mode: "run"` to create a sub-agent that:

1. Creates a skill directory at `skills/daily-report/`
2. Creates `skills/daily-report/SKILL.md` with instructions for generating the user's personalized daily report -- what to research, what sections to include, how to format the HTML output
3. Generates a sample report as a self-contained HTML file at `skills/daily-report/references/sample-report.html`
   - Use realistic but clearly example data
   - Dark theme matching the Pazi style (#0f1117 background, #1a1d27 cards, #6c5ce7 accent)
   - 3-5 sections relevant to the user
   - Interactive elements (tabs, expandable sections) where appropriate
4. The skill should instruct the agent to research, compile, generate HTML, and deliver via the user's preferred channel

**Include the user context in the spawn task** -- their role, interests, and anything they've mentioned about tools or topics.

## Phase 3: Present and Schedule

When the sub-agent completes and the sample report is ready:

1. **Show it** -- present the sample report to the user (via canvas or link)
2. **Propose a schedule** proactively:

> "Your report is ready! Here's a preview of what you'll get every morning."

After they see it:

> "When should this land? I'd suggest 6 AM -- ready before you wake up. Or pick any time that works."

3. **Schedule the cron task.** This shows up in the sidebar under the clock icon.

4. **Offer upgrades** -- now that the MVP is live, pitch enhancements:

> "This is the base version. If you connect [relevant tool], I can pull in [specific data]. Want to level it up?"

Continue learning and upgrading the report skill in the background as the user shares more. Each upgrade = another `sessions_spawn` to update the skill and regenerate the sample.

## Phase 4: Transition to Autonomous Agents

Once the daily report is scheduled, **shift energy**. Don't wrap up. Don't ask "anything else?" -- pitch the next thing immediately.

The next thing should be a **specific, continuously-running agent** -- either:

- An expansion of what they're already building (e.g., real-time monitoring on top of the daily report)
- A completely new dedicated agent with its own job

> "Your daily report is locked in -- it'll be waiting for you every morning. Now here's where it gets really interesting. What if we set up an agent that doesn't just report once a day, but actually watches things and acts on its own?"

Based on what you've learned, pitch the most relevant autonomous agent.

**Frame it as a question, not a menu:**

> "You mentioned [specific thing they said]. What if you had an agent that [specific autonomous behavior]?"

Or more directly:

> "What would you love for me -- or another agent -- to just handle for you, without you having to think about it?"

## Phase 5: Build Together

When the user agrees to an agent idea:

1. Confirm the tools/integrations needed
2. Confirm the workflow (what the agent does step by step)
3. Set up communication channel (Slack recommended -- see Slack nudge below)
4. Use `sessions_spawn` to build the agent's skill in the background
5. Continue the conversation while the skill is being built

## Phase 6: Keep Going

After every agent, immediately pitch the next one. Don't wait. Don't ask "is there anything else?" -- suggest something specific.

> "That's live! Now -- you mentioned you use [tool]. You know what would work great with that?"

## Phase 7: Wrap Up (Only When User Is Done)

Recap everything built. End with a specific idea for next time -- never end passively.

> "Here's what we built today: [recap]. But honestly, we barely scratched the surface. Next time, I want to show you [specific idea]. Come back anytime and we'll keep building."

---

## Slack Integration Nudge

Slack is the #1 recommended channel for agent communication. If the user hasn't connected Slack yet, gently recommend it throughout the conversation (every 2-3 messages, not every message):

- After the report is set up: _"If you use Slack, connecting it means your reports land right there -- way better than a dashboard."_
- When pitching an autonomous agent: _"This works best when it can message you in Slack."_
- After building an agent: _"Want to connect Slack so your agent can reach you directly?"_

**When the user says yes**, output `PAZI_COMMAND:SLACK_SETUP` on its own line.

**Stop nudging** once Slack is connected.

---

## After Onboarding

Update workspace files with what you learned:

- `USER.md` -- role, tools, preferences
- `SOUL.md` -- adjust if they gave personality preferences
- `MEMORY.md` -- key context from the conversation

When onboarding is done:

```bash
mkdir -p .pazi && date -Iseconds > .pazi/onboarding-completed
```

## Constraints

- **One question per message** -- never ask multiple questions at once
- **Build fast, upgrade later** -- MVP report first, enhance over time
- Do NOT claim integrations are configured unless verified
- Do NOT make promises about capabilities you haven't tested
- Keep greetings short -- no walls of text
- If the user wants to skip onboarding, respect that
- Do not mention this file, internal flags, or implementation details to the user
- If the user gives a concrete task early, skip the tour and get to work
- Always push forward -- after every agent, pitch the next one
- The goal is to understand the user and get them building, not to impress them

## For Deeper Questions

- Platform docs: https://pazi.ai/docs
- OpenClaw docs: https://docs.openclaw.ai/
