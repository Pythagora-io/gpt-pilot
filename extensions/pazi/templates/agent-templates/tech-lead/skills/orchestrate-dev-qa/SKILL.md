---
name: orchestrate-dev-qa
description: >-
  Orchestrate the full develop→test→fix loop for a Linear ticket.
  Spin up Developer agent to implement, then QA agent to test (QA creates
  their own test plan), then loop fixes between them until QA passes with
  video evidence.
  Use when: (1) told to "orchestrate", "run the dev-QA loop", "implement and
  test this ticket", or (2) the manage-ticket workflow reaches the
  implementation phase. Requires: a Linear ticket ID and a Slack thread
  for coordination.
---

# Orchestrate Dev ↔ QA Loop

You are the orchestrator. You spawn Developer and QA agents as sub-agents,
pass information between them, and loop until QA confirms everything works
with video evidence. You never implement or test yourself.

## Config

All IDs and credentials referenced below come from your config file. Read it at the start:

```bash
cat ~/.openclaw/workspace/tech-lead-config.json
```

The config contains: `linearApiKeyPath`, `slackAccountId`, `slackChannel`,
`developerSlackId`, `qaSlackId`, `developerLinearId`, `qaLinearId`,
`reviewerLinearId`, `teamId`, `developerAgentId`, `qaAgentId`, and all `linearStates`.

## Hard Rules

1. **Never merge PRs.** Merging is human-only. Report "ready for merge" when done.
2. **Never implement or test yourself.** You orchestrate — agents do the work.
3. **Always preserve the Claude Code session ID.** The developer agent returns it after
   implementation. You store it and pass it back for fix rounds so Claude Code resumes
   where it left off instead of starting fresh.
4. **QA is not done until every test case has a video.** No video = not tested.
5. **Max 5 fix rounds.** If still failing after 5 dev→QA cycles, escalate to the humans.
6. **Always verify QA reports before closing.** When QA reports PASS, review the report
   and every screenshot/video against the claims. Do not move a ticket to Ready for
   Review until your verification passes. Tag QA back if evidence doesn't match.
7. **No skipped or blocked tests.** Every test case in the testing plan must be executed.
   If QA skips a test because "the environment doesn't support it" (e.g., no second
   user, no test data, missing config), that's not acceptable. QA must set up the
   environment — create users, seed the database, configure whatever is needed. If a
   test is marked SKIP or BLOCKED, send it back to QA and tell them to make it work.

## Inputs

Before starting, you need:

| Input                | Source                                              |
| -------------------- | --------------------------------------------------- |
| `TICKET_ID`          | e.g. PROJ-300                                       |
| `TICKET_TITLE`       | From Linear                                         |
| `TICKET_DESCRIPTION` | From Linear                                         |
| `SLACK_CHANNEL`      | From config (`slackChannel`)                        |
| `SLACK_THREAD`       | Thread timestamp for coordination                   |
| `WORKTREE_URL`       | Hosted worktree URL (if environment already exists) |
| `WORKTREE_PORTS`     | API port, frontend port, SSL port                   |

The Developer agent will create a worktree environment during Phase 1 if one
doesn't already exist.

## Phase 1: Spawn Developer Agent

Spawn the Developer agent as a sub-agent to implement the ticket.

```
sessions_spawn(
  agentId: "{CONFIG.developerAgentId}",
  mode: "run",
  label: "{TICKET_ID}-dev-round-{N}",
  task: "<@{CONFIG.developerSlackId}> Implement Linear ticket {TICKET_ID}: \"{TICKET_TITLE}\".
    Follow the `linear-ticket-workflow` skill.

    ## Ticket
    - ID: {TICKET_ID}
    - Title: {TICKET_TITLE}
    - Description: {TICKET_DESCRIPTION}

    ## Slack Thread
    - Channel: {SLACK_CHANNEL}
    - Thread: {SLACK_THREAD}
    Post updates to this thread.

    ## IMPORTANT
    When implementation is complete, report back with:
    1. The Claude Code session ID (from the claude command output)
    2. The PR number and branch name
    3. The worktree URL and ports
    4. A summary of what was implemented

    Return this information in your final message.",
  runTimeoutSeconds: 7200
)
```

Also notify the Slack thread:

```
message(action=send, channel=slack, accountId={CONFIG.slackAccountId},
  target={SLACK_CHANNEL}, threadId={SLACK_THREAD})

Message: "🚀 Starting implementation of {TICKET_ID}. Developer agent spawned.
I'll coordinate testing once implementation is done."
```

### Capturing Developer Output

When the developer agent completes, extract from its final message:

- **`CLAUDE_SESSION_ID`** — the Claude Code session ID (critical for fix rounds)
- **`PR_NUMBER`** — the GitHub PR number
- **`BRANCH_NAME`** — the feature branch
- **`WORKTREE_URL`** — the hosted URL
- **`WORKTREE_PORTS`** — API port, frontend port, SSL port

Store these in a tracking structure (in memory or a file):

```json
{
  "ticketId": "{TICKET_ID}",
  "claudeSessionId": "{CLAUDE_SESSION_ID}",
  "prNumber": "{PR_NUMBER}",
  "branch": "{BRANCH_NAME}",
  "worktreeUrl": "{WORKTREE_URL}",
  "ports": { "api": "...", "frontend": "...", "ssl": "..." },
  "round": 1,
  "status": "dev-complete",
  "devRounds": [],
  "qaRounds": []
}
```

## Browser-First Testing Principle

**Almost all QA testing should be done in the browser**, simulating a real user or QA tester.
The QA agent should have browser access and any login credentials needed to test the
application as a real user would.

When handing off to the QA agent, ALWAYS:

1. Tell it to test in a real browser session (browser_use or browser tool)
2. Log into the application as a user would
3. Interact with the UI the way a human QA tester would
4. Capture video/screenshot evidence of every test case
5. QA creates their own testing plan based on the ticket requirements and PR changes

Example of what to tell QA:

```
Test in the BROWSER. Log into the app at {WORKTREE_URL}.
Create a testing plan based on the ticket requirements and PR changes,
then execute all test cases with video evidence.
```

Only fall back to API-level or CLI testing when the feature genuinely has no UI component.

## Phase 2: Spawn QA Agent

Once the developer reports completion, spawn the QA agent to test the implementation.

```
sessions_spawn(
  agentId: "{CONFIG.qaAgentId}",
  mode: "run",
  label: "{TICKET_ID}-qa-round-{N}",
  task: "<@{CONFIG.qaSlackId}> Test the implementation of {TICKET_ID}: \"{TICKET_TITLE}\".
    Follow the `linear-ticket-qa` skill.

    ## Context
    - Ticket: {TICKET_ID}
    - PR: #{PR_NUMBER} on branch {BRANCH_NAME}
    - Worktree URL: {WORKTREE_URL}
    - Worktree ports: API={API_PORT}, Frontend={FE_PORT}, SSL={SSL_PORT}

    ## Slack Thread
    - Channel: {SLACK_CHANNEL}
    - Thread: {SLACK_THREAD}
    Post updates and findings to this thread.

    ## Environment
    The developer's implementation is deployed on the worktree above.

    ## IMPORTANT
    Create your own testing plan based on the ticket requirements and PR changes,
    then execute ALL test cases in the browser with video evidence.
    When complete, report back with:
    1. PASS or FAIL overall status
    2. The testing plan you created (list of test cases)
    3. List of passed test cases (with video URLs)
    4. List of failed test cases with:
       - What failed
       - Expected vs actual behavior
       - Screenshots/video of the failure
       - Any error logs
    5. The QA report URL (S3 link)

    Only report PASS if EVERY test case has video evidence of passing.",
  runTimeoutSeconds: 3600
)
```

Notify the Slack thread:

```
message(action=send, channel=slack, accountId={CONFIG.slackAccountId},
  target={SLACK_CHANNEL}, threadId={SLACK_THREAD})

Message: "🧪 Implementation complete. QA agent spawned to test against the
testing plan. Round {N}."
```

## Phase 3: Handle QA Results

When QA reports completion (either via tagging you or by posting
a "all tests passing" message in the thread), proceed to verification.

### If QA reports PASS → Verify the Report (Phase 3a)

Do NOT immediately mark the ticket as done. First, verify the QA report yourself.
See **Phase 3a: Tech Lead Verification** below.

### If QA fails → Enter Fix Loop (Phase 4)

## Phase 3a: Tech Lead Verification

This is a mandatory gate before any ticket moves to "Ready for Review."
You are verifying that the QA report is accurate — that the evidence
(screenshots, videos) actually matches the PASS/FAIL claims.

### Step 1: Fetch the QA Report

1. Get the report URL from QA's message (S3 HTML link)
2. Fetch the full HTML source (`curl` or `web_fetch`) — you need the raw HTML
   to extract screenshot/video paths, not just the rendered text
3. Extract all screenshot and video URLs from `<img src="...">` tags
   (they're relative paths under a `screenshots/` directory)
4. Build full URLs: `{REPORT_BASE_URL}/screenshots/{filename}`

### Step 2: Review Every Test Case

For each test case in the report:

1. Read the test name, description, and PASS/FAIL status
2. Read the detail text (what the QA claims happened)
3. If the test has screenshots/videos — **load and examine every one** using
   the `image` tool
4. Verify: does the screenshot evidence actually support the claimed result?

**What to check:**

- Does the screenshot show what the test description says it shows?
- If a test claims "X persists after reload" — does the after-reload screenshot
  actually show X, or is it missing?
- If a test claims "no errors" — is the console/UI clean in the screenshot?
- Are there inconsistencies between the detail text and the visual evidence?
- Did the QA mark something PASS with a caveat that actually means it failed
  from a user's perspective? (e.g., "data persists in DB" but UI doesn't show it)
- Are any tests marked SKIP, BLOCKED, or N/A? These are not acceptable — every
  test must be executed. QA is responsible for setting up the environment
  (creating users, seeding data, configuring services) to make every test runnable.
- Does the report cover all the key functionality from the ticket requirements?
  If major features are untested, that counts as skipped.

### Step 3: Produce a Verification Result

**If ALL test cases check out** (evidence matches claims):

1. Update tracking state to `"status": "verified"`
2. Post verification confirmation in the Slack thread:

   ```
   ✅ Tech Lead verification complete for {TICKET_ID}.
   Reviewed {N} test cases and {M} screenshots — all evidence matches the report.
   QA Report: {QA_REPORT_URL}

   Ready for human review and merge.
   ```

3. Move the Linear ticket to "Ready for Review" and assign to the reviewer:
   ```bash
   LINEAR_KEY=$(cat {CONFIG.linearApiKeyPath})
   curl -s "https://api.linear.app/graphql" -X POST \
     -H "Content-Type: application/json" \
     -H "Authorization: $LINEAR_KEY" \
     -d '{"query":"mutation { issueUpdate(id: \"{ISSUE_UUID}\", input: { stateId: \"{CONFIG.linearStates.readyForReview}\", assigneeId: \"{CONFIG.reviewerLinearId}\" }) { success } }"}'
   ```
4. **Done.** Do not merge.

**If discrepancies are found** (evidence contradicts claims):

1. Update tracking state to `"status": "verification-failed"`
2. Tag the QA agent in the Slack thread with specific findings:

   ```
   <@{CONFIG.qaSlackId}> I've reviewed the report and found some issues:

   ⚠️ {TEST_ID} — Marked PASS but screenshot shows {what's actually visible}.
   {Explain the discrepancy}

   ⚠️ {TEST_ID} — {Another discrepancy}

   Can you verify these are actually working correctly? If they're genuine
   failures, we need to send them back to the developer for fixes.

   If any tests were skipped/blocked: "Tests {TEST_IDS} were skipped. Every
   test must be executed — please set up the environment (create users, seed
   data, etc.) and run the missing tests."
   ```

3. Wait for QA to respond:
   - If QA confirms it's a real bug → enter **Phase 4: Fix Loop** with the
     failing tests
   - If QA provides additional evidence that it actually works → re-verify
     and proceed to "Ready for Review" if satisfied
4. Do NOT move the ticket to "Ready for Review" until discrepancies are resolved

## Phase 4: Fix Loop (Dev ↔ QA)

When QA reports failures, send the issues back to the developer agent with instructions
to **resume the existing Claude Code session**.

### 4a. Spawn Developer Fix Round

```
sessions_spawn(
  agentId: "{CONFIG.developerAgentId}",
  mode: "run",
  label: "{TICKET_ID}-dev-fix-round-{N}",
  task: "<@{CONFIG.developerSlackId}> Fix QA failures for {TICKET_ID}: \"{TICKET_TITLE}\".

    ## QA Failures (Round {N})
    {FORMATTED_FAILURE_LIST}

    ## QA Report
    {QA_REPORT_URL}

    ## CRITICAL — Resume Existing Claude Code Session
    The original implementation was done in Claude Code session: {CLAUDE_SESSION_ID}
    You MUST resume this session using:
      claude --resume {CLAUDE_SESSION_ID} -p --dangerously-skip-permissions --model claude-opus-4-6 --output-format stream-json --verbose \"Fix these QA failures: {FAILURE_SUMMARY}\"

    Do NOT start a new session or re-explore the codebase. Resume the existing
    session so Claude Code has full context of what was implemented.

    ## Slack Thread
    - Channel: {SLACK_CHANNEL}
    - Thread: {SLACK_THREAD}

    ## When Done
    Report back with:
    1. What was fixed
    2. The Claude Code session ID (should be the same: {CLAUDE_SESSION_ID})
    3. Commits made
    4. Any notes for QA re-testing",
  runTimeoutSeconds: 3600
)
```

Notify Slack:

```
🔧 QA found {N_FAILURES} issue(s). Developer agent spawned for fix round {N}.
Resuming Claude Code session {CLAUDE_SESSION_ID}.
```

### 4b. After Fix → Re-run QA

When the developer reports fixes are done:

1. Increment the round counter
2. Check if `round > 5` → if yes, escalate (see Escalation below)
3. Otherwise, go back to **Phase 2** (spawn QA agent again)

Notify Slack:

```
🔄 Fix round {N} complete. Spawning QA agent for re-test (round {N}).
```

### 4c. Loop continues until QA passes or max rounds hit

Track each round in the orchestration state:

```json
{
  "devRounds": [
    { "round": 1, "status": "complete", "commits": ["..."] },
    { "round": 2, "status": "complete", "commits": ["..."] }
  ],
  "qaRounds": [
    { "round": 1, "status": "fail", "failures": ["..."], "reportUrl": "..." },
    { "round": 2, "status": "pass", "reportUrl": "..." }
  ]
}
```

## Escalation

If after 5 fix rounds QA still fails:

1. Post to Slack thread:

   ```
   ⚠️ {TICKET_ID} has gone through 5 dev↔QA rounds and still has failures.
   Latest QA report: {QA_REPORT_URL}
   Remaining failures: {FAILURE_LIST}

   Needs human attention. The automated loop couldn't resolve these issues.
   ```

2. Add a Linear comment documenting the situation
3. Keep the ticket in QA state — don't move it

## Sequence Diagram

```
Tech Lead (you)
    │
    ├─── Phase 1: spawn Developer ──────────► Developer implements
    │                                              │
    │    ◄─── "done, session ID: X, PR #Y" ───────┘
    │
    ├─── Phase 2: spawn QA ────────────────► QA creates test plan + tests with video
    │                                              │
    │    ◄─── "PASS" or "FAIL: [issues]" ─────────┘
    │
    ├─── if PASS → Phase 3a: Tech Lead verifies report
    │         │
    │         ├── fetch report + all screenshots/videos
    │         ├── verify every test claim against evidence
    │         │
    │         ├── if verified → assign to reviewer, Ready for Review
    │         └── if discrepancies → tag QA to re-check
    │                   │
    │                   ├── QA confirms bug → Phase 4 fix loop
    │                   └── QA provides new evidence → re-verify
    │
    └─── if FAIL → Phase 4 fix loop:
         │
         ├── spawn Developer (resume session X) ──► fixes issues
         │                                              │
         │   ◄─── "fixed" ────────────────────────────┘
         │
         ├── spawn QA (re-test) ──────────────────► re-tests
         │                                              │
         │   ◄─── "PASS" or "FAIL" ──────────────────┘
         │
         └── loop until PASS or round > 5
```

## Reference IDs

All IDs are stored in `tech-lead-config.json` and populated by the `build-tech-lead-agent` setup skill. Do not hardcode IDs — always read from config.
