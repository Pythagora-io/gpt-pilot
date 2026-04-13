---
name: qa-phase0
description: >-
  Phase 0: Pre-QA preparation. Use after qa-flow is read — never as a direct entry point.
  Creates the test folder, checks the queue, loads knowledge base, fetches ticket/PR info,
  reproduces bugs, and writes the testing plan that all subsequent phases use.
---

# Phase 0: Pre-QA

First phase of every testing session. Creates the test folder, analyzes what needs
testing, reproduces bugs, and writes the testing plan that all subsequent phases use.

**Before starting:** Read `environment.md` in the template root to resolve all
environment-specific values.

## Hard Rules

1. **Use the `browser` tool for all browser automation.** Use the built-in `browser` tool (snapshot + act) in **headed mode** (not headless). Do NOT use Playwright, `browser_use`, or any external browser automation library.
2. **Test environments: QA/staging or production ONLY.** Never localhost. Never worktrees.
3. **The testing plan is the single source of truth.** Everything downstream depends on it.
4. **`testing-plan.md` is write-once.** Create it here, then never modify it again. It is the original plan. During phase 3, only `test-cases.json` gets updated with results.

## Step 0: Queue — DO THIS FIRST BEFORE ANYTHING ELSE

Use the queue script to add this test:

```bash
python3 skills/qa-queue/queue.py add \
  --id PAZ-XXX \
  --type ticket \
  --description "Short description" \
  --prs "{PLATFORM_REPO}#501,{AGENT_REPO}#141" \
  --requestedBy <requester> \
  --slackChannel {SLACK_PRIMARY_CHANNEL_ID} \
  --slackThread "1775..."
```

**After running the script, reply to the requester** (same channel/thread) so they know what's happening — whether it's starting now or queued behind something else.

If `STARTED` → let them know you're on it, then continue to Step 1.
If `QUEUED` → let them know it's in the queue and what's ahead of it, then **STOP. Do not continue.**

**Do NOT proceed to Step 1 unless the script confirmed this test is `current`.**

## Workflow

### 1. Create Test Folder

Create a dedicated folder for this entire test run. ALL artifacts for all phases go here.

```bash
RUN_ID="qa-PAZ-XXX-$(date +%Y%m%d-%H%M%S)"
TEST_DIR="{WORKSPACE_DIR}/{TEST_RUNS_DIR}/$RUN_ID"
mkdir -p "$TEST_DIR/screenshots"
```

**Update the queue** with the test folder path:

```json
{ "testFolder": "{TEST_RUNS_DIR}/qa-PAZ-XXX-20260407-190000" }
```

### 2. Environment

**Default: QA/staging environment.** Unless explicitly told to test on production, all testing
happens on your QA environment. You have full admin access to the entire cloud account,
MongoDB, Redis, S3, ECR, and all EC2 instances. You can do whatever you need for testing —
seed data, modify credits, restart services, create databases, SSH into any instance.

Only use production if the user explicitly says "test production".

### 2b. Top Up QA Credits (QA env ONLY — MANDATORY)

Before any testing, ensure the QA account has sufficient credits.

```bash
# Get the MongoDB connection string from the API env or via get_credential
MONGO_URI=$(ssh -o StrictHostKeyChecking=no -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP} "grep MONGODB_URI ~/.env.production" | cut -d= -f2-)

# Top up credits for the QA user (adapt the collection/field names to your data model)
mongosh "$MONGO_URI" --quiet --eval "
  // Find the user and update their credits
  // Adapt this query to match your application's data model
  db.users.updateOne(
    {email: '{TEST_ACCOUNT_EMAIL}'},
    {\$set: {credits: 50000}}
  );
"
```

**IMPORTANT:** Check your application's data model to understand which collection/table
stores the credits that the UI actually reads. Some apps separate user accounts from
billing/customer records — make sure you update the right one.

### 3. Load Knowledge Base Context

Load platform knowledge BEFORE analyzing the ticket:

1. Read `knowledgebase/README.md` at `{KNOWLEDGEBASE_PATH}/README.md`
2. Load relevant `platform/*.md` files based on the area being tested
3. Read `bugs/patterns.md` — recurring bug patterns
4. Read `bugs/known-issues.md` — active known bugs

| If it involves... | Load                            |
| ----------------- | ------------------------------- |
| Onboarding        | `platform/onboarding.md`        |
| Agent creation    | `platform/agent-creation.md`    |
| Skills            | `platform/skills.md`            |
| Dashboard/chat    | `platform/dashboard.md`         |
| Scheduled tasks   | `platform/scheduled-tasks.md`   |
| Slack             | `platform/channels/slack.md`    |
| Discord           | `platform/channels/discord.md`  |
| Telegram          | `platform/channels/telegram.md` |
| WhatsApp          | `platform/channels/whatsapp.md` |
| Billing           | `platform/billing.md`           |
| Analytics         | `platform/analytics.md`         |
| Integrations      | `platform/integrations.md`      |

### 4. Fetch Ticket/PR Information

**For Linear tickets:**

```bash
# Use the Linear skill to fetch ticket info
python3 skills/linear/scripts/linear_api.py --api-key "$LINEAR_KEY" issue --id "PAZ-XXX"
```

Claim the ticket — assign to QA and set status:

```bash
python3 skills/linear/scripts/linear_api.py --api-key "$LINEAR_KEY" update-issue \
  --id "PAZ-XXX" \
  --assignee-id "{LINEAR_QA_USER_ID}" \
  --state-id "{LINEAR_QA_STATE_ID}"
```

**For PRs:**

```bash
gh pr view <number> --repo {GITHUB_ORG}/{PLATFORM_REPO} --json title,body,files,url
gh pr diff <number> --repo {GITHUB_ORG}/{PLATFORM_REPO}
```

Search for companion PRs:

```bash
gh search prs "PAZ-XXX" --owner {GITHUB_ORG} --json url,title,state --limit 5
```

Extract: title, description, files changed, companion PRs, what the developer did NOT verify.

### 5. Reproduce the Bug (bugs only — MANDATORY)

**For bug tickets:** You MUST reproduce the bug before writing the testing plan.

- Deploy `main` branch to QA env (or test on production if it's a production bug)
- Reproduce via the `browser` tool — navigate, click, interact as a real user would
- Take screenshots as evidence: `$TEST_DIR/screenshots/reproduction/NNN-description.png`
- Document exact reproduction steps with timing
- Confirm any workaround mentioned in the ticket

**For new features touching existing behavior:** Record the CURRENT state before changes (the "before" baseline).

**For net-new features (no existing UI):** Skip reproduction, go to step 6.

**If you cannot reproduce:**

- Document exactly what you tried and why
- Do NOT hand off to developer — escalate to team lead
- Assign to team lead in Linear, set to Todo, message in Slack thread

### 6. Write the Testing Plan

You must create **two files** — a human-readable markdown plan AND a structured JSON file
that the QA agent follows during execution. Both live in `$TEST_DIR`.

#### 6a. Markdown Plan: `$TEST_DIR/testing-plan.md`

Human-readable plan. **Write-once — never modified after creation.** This is the original
test plan that documents what will be tested and why. Results go in `test-cases.json` only.

**Every test case must include detailed step-by-step execution instructions.** A test case
is only valid if someone who has never seen the feature can execute it by following the
steps alone. If a step says "verify the result" without saying what the result looks like,
it's not a test — it's a wish.

For each test case, write:

- **Numbered steps** with exact actions ("Click the 'DM Access' dropdown", not "change settings")
- **Specific inputs** — exact values to type, exact messages to send, exact IDs to use
- **Exact expected output** — the precise text, state, or behavior
- **curl commands** for any API test or UI-bypass scenario (ready to copy-paste)
- **Prerequisites per test** if it depends on a prior test's state

```markdown
# Testing Plan — {what's being tested}

## Meta

- **Ticket:** PAZ-XXX
- **PR(s):** {PLATFORM_REPO}#{N}, {AGENT_REPO}#{N}
- **Environment:** QA / Production
- **Test Account:** {TEST_ACCOUNT_EMAIL} / {TEST_ACCOUNT_PASSWORD}
- **Run ID:** {run-id}
- **Test Folder:** {test-folder-path}
- **Date:** {date}
- **Status:** PRE-QA | PHASE1 | PHASE2 | PHASE3 | PHASE4 | COMPLETE

## Prerequisites

{What must be true before ANY test runs — accounts, tokens, environment state, tools needed}

## Summary

{1-2 paragraphs: what changed, what needs testing, key risks}

## Reproduction Evidence (bugs only)

{Steps, screenshots, what was broken, "before" baseline}

## Test Cases

### PW-1.1 · Test Name [HIGH]

**Steps:**

1. Open browser → navigate to `{APP_URL}/login`
2. Log in with `{TEST_ACCOUNT_EMAIL}` / `{TEST_ACCOUNT_PASSWORD}`
3. Click "Agent setup" in the left sidebar
4. {specific action with specific value}

**Expected:**

- {Exact observable outcome}
- {Screenshot instruction if applicable}
```

#### 6b. Structured Test Plan: `$TEST_DIR/test-cases.json`

**Derived from `testing-plan.md`.** This is the machine-readable version that the QA agent
follows step by step during phase 3. Create it by converting the markdown plan into the
JSON structure below. It has two mandatory sections: **API tests** and **browser tests**.
Both sections MUST be executed — they are different types of testing and both are required.

This is the ONLY file that gets updated with results during phase 3.

```json
{
  "meta": {
    "id": "PAZ-XXX",
    "runId": "qa-PAZ-XXX-20260408-060000",
    "environment": "qa",
    "baseUrl": "{APP_URL}",
    "apiUrl": "{API_URL}",
    "testAccount": {
      "email": "{TEST_ACCOUNT_EMAIL}",
      "password": "{TEST_ACCOUNT_PASSWORD}"
    },
    "date": "2026-04-08",
    "status": "PRE-QA",
    "prerequisites": [
      "Deploy feature branches to QA environment",
      "Log into QA environment with test account",
      "Any other setup needed"
    ]
  },
  "summary": "Short description of what's being tested and why",
  "apiTests": [
    {
      "id": "API-1.1",
      "name": "Test description",
      "priority": "HIGH",
      "method": "RPC",
      "endpoint": "endpoint.method",
      "headers": {},
      "body": {},
      "curlCommand": "curl -X POST {API_URL}/gateway/rpc -H 'Cookie: <session>' -H 'Content-Type: application/json' -d '{...}'",
      "expectedStatus": 200,
      "expectedBody": null,
      "assertions": ["assertion 1", "assertion 2"],
      "status": "PENDING",
      "actualStatus": null,
      "actualBody": null,
      "notes": "",
      "error": null
    }
  ],
  "browserTests": [
    {
      "id": "PW-1.1",
      "name": "Test description",
      "priority": "HIGH",
      "steps": [
        "Navigate to {APP_URL}/login",
        "Log in with {TEST_ACCOUNT_EMAIL} / {TEST_ACCOUNT_PASSWORD}",
        "Perform specific actions"
      ],
      "expected": "Exact observable outcome.",
      "testInputs": {
        "account": "{TEST_ACCOUNT_EMAIL}",
        "password": "{TEST_ACCOUNT_PASSWORD}"
      },
      "status": "PENDING",
      "screenshots": [],
      "screenshotVerification": "",
      "screenshotMatchesExpected": null,
      "notes": "",
      "error": null
    }
  ]
}
```

#### JSON Test Plan Rules

- **`apiTests`** — Tests that call API endpoints directly (curl/fetch). Verify backend logic,
  status codes, response bodies, auth, error handling. Use for: health checks, CRUD operations,
  auth flows, webhook endpoints, data validation.
- **`browserTests`** — Tests that interact with the UI via the `browser` tool. Verify user-visible
  behavior, UI rendering, navigation, forms, visual state. Use for: feature workflows, UI
  components, user journeys, visual regression.
- **Both sections are MANDATORY.** Every test run must have API tests AND browser tests.
  If a change is purely backend, still add basic browser smoke tests (login, page loads).
  If a change is purely frontend, still add API tests (endpoints still return correct data).
- **`meta.prerequisites`** — Array of strings listing what must be true before any test runs
  (accounts, tokens, environment state, third-party access). Forces explicit planning.
- **IDs:** API tests use `API-X.Y`, browser tests use `PW-X.Y`
- **Priority:** `HIGH` or `NORMAL` — same rules as markdown plan
- **Status values:** `PENDING`, `RUNNING`, `PASS`, `FAIL`, `BLOCKED`, `NEED_HELP`
- **API test fields:**
  - `curlCommand` — **MANDATORY.** Ready-to-copy-paste curl command (or RPC call) to execute the test.
    Anyone should be able to run this without assembling the request manually.
- **Browser test fields:**
  - `steps` — **Detailed numbered steps.** Each step must be specific enough for someone who has
    never seen the feature. Bad: `"Verify the result"`. Good: `"Verify DM Access dropdown shows 'Closed' by default"`.
  - `expected` — Exact observable outcome with precise text, states, or timing.
  - `testInputs` — **MANDATORY object.** Concrete values used in this test: IDs, messages,
    field values, expected response text. Forces the plan writer to be concrete.
  - `status` — `"PASS"`, `"FAIL"`, `"BLOCKED"`, or `"NEED_HELP"`. Based on screenshot verification — the screenshot is ground truth.
  - `screenshotVerification` — **MANDATORY.** Brief description of what each screenshot actually shows. If this field is empty, the test result is invalid.
  - `screenshotMatchesExpected` — **MANDATORY boolean.** `true` if the screenshot shows what the test expected, `false` if it doesn't. If `false`, status MUST be `FAIL` — no exceptions.
  - `screenshots` — Array of screenshot file paths.
  - `notes` — What you observed, deviations from expected behavior.
  - `error` — Error message if failed.
- **During phase 3:** Update all fields as each test completes. The JSON is the source of truth for execution state.

#### What makes a good plan

Think adversarially. For EACH change:

- **Happy path** — does the feature work as described?
- **Edge cases** — empty inputs, special characters, very long text, zero values
- **Error handling** — network errors, 404s, permission denied
- **State transitions** — page refresh, browser back, tab switching
- **Regression** — did the change break nearby functionality?
- **Concurrent access** — double-click, rapid actions, multiple tabs

Use knowledge base context: `bugs/patterns.md` for recurring patterns, `platform/*.md` for historical gotchas.

**The granularity test:** Every test must be executable by someone who has never seen the
feature. If a step says "verify the result" without saying what the result looks like, it's
not a test — it's a wish. If an API test doesn't include a ready-to-run curl command, it's
incomplete. If a browser test doesn't specify the exact text to type or the exact button
to click, rewrite it.

**Scale with PR size:**

- Small (1-3 files): 5-10 test cases total (across both sections)
- Medium (4-10 files): 10-20 test cases total
- Large (10+ files): 20-40 test cases total

Always at least 3 HIGH and 3 NORMAL priority tests across both sections.

### 7. Build Pre-QA Report & Post to Linear

Build an HTML report using the `build-report` skill:

1. **Ticket summary** — ID, title, priority
2. **Reproduction evidence** (bugs) — screenshots showing the broken state
3. **Testing plan** — all test cases

Upload to S3:

```bash
aws s3 cp "$TEST_DIR/qa-phase0-report.html" \
  "s3://{S3_PUBLIC_BUCKET}/{S3_REPORTS_PREFIX}$RUN_ID/qa-phase0-report.html" \
  --content-type "text/html" --profile {AWS_PROFILE}
```

Report URL: `{S3_REPORTS_URL_BASE}/$RUN_ID/qa-phase0-report.html`

Save locally too: `$TEST_DIR/qa-phase0-report.html`

Post a short comment to Linear:

```bash
python3 skills/linear/scripts/linear_api.py --api-key "$LINEAR_KEY" comment \
  --issue-id "PAZ-XXX" \
  --body "## Pre-QA Report
Report: <url>
Summary: <1-2 lines>"
```

### 8. Handoff & Phase Transition

**For pre-implementation tickets (bug needs fixing / feature needs building):**
Assign to developer agent, tag in Slack thread:

```
<@{SLACK_DEVELOPER_AGENT_ID}> can you implement this - PAZ-XXX - make sure to follow `linear-ticket-workflow` skill
```

**For post-implementation testing (PR is ready):**
Update queue phase to `phase1` and proceed to `qa-phase1`.

### 9. Update Queue

```bash
python3 skills/qa-queue/queue.py update-phase \
  --phase qa-phase0-done \
  --notes "Testing plan written with N test cases (X HIGH, Y NORMAL). Reproduction: success/failed/skipped."

python3 skills/qa-queue/queue.py edit --field testFolder --value "{TEST_RUNS_DIR}/$RUN_ID"
```

## Key Principles

- **Reproduce first, always** (for bugs). No reproduction = can't verify a fix later.
- **Think like an attacker.** What breaks? What was missed?
- **Be specific.** "Check that it works" is not a test case.
- **You own production quality.** If a bug slips through your plan, it's on you.
