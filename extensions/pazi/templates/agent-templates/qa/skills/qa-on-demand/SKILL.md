---
name: qa-on-demand
description: >-
  Run comprehensive QA tests on-demand — test the entire platform or specific areas.
  Uses a Manager/Executor agent pattern: Manager orchestrates, Executors do browser testing.
  Completely independent from the Linear ticket pipeline. No queue, no PR, no Linear.
  Triggers: "full QA", "test everything", "test Slack", "test billing", "test onboarding",
  "QA on demand", "regression test", "test [area]".
metadata:
  openclaw:
    emoji: "🧪"
---

# QA On-Demand

Run comprehensive QA tests against the platform — the whole thing or specific areas.
Uses a **Manager/Executor agent pattern** for reliable, parallelizable test execution.
Completely independent from the ticket-based QA pipeline (no Linear, no queue, no PR).

**Before starting:** Read `environment.md` in the template root to resolve all
environment-specific values.

## When to Use

- "Full QA" / "test everything" / "regression" → run all areas
- "Test Slack" / "test billing" / "test onboarding" → run specific area(s)
- "Smoke test" → run only HIGH priority tests from all suites
- Before a release → run all areas
- After a deploy → run smoke test (subset)

## What This Is NOT

- Not tied to Linear tickets or PRs
- Not using the QA queue (that's for ticket QA only)
- Not deploying branches — tests whatever is currently running on the target environment

## Architecture — Manager/Executor Pattern

```
You (main agent — loads this skill, builds test plan)
  └─► QA Manager (persistent session, mode="session")
        ├─► Executor 1 (run mode, batch of 3-5 tests)
        ├─► Executor 2 (run mode, next batch)
        ├─► Executor 3 (parallel if independent sections + different test accounts)
        └─► ... until all tests executed
              └─► Manager builds HTML report, returns results
```

### Why This Pattern?

- **Manager never loses progress** — tracker file persists across executor rounds
- **Executors are disposable** — if one hangs or crashes, Manager marks tests as BLOCKED and moves on
- **Parallel execution** — independent areas can run simultaneously with different test accounts
- **Focused context** — each Executor gets only 3-5 test cases (stays under context limits)
- **Reliable completion** — Manager keeps spawning Executors until every test has a result

## Target Environments

| Environment  | URL                    | Login                                                     | When                         |
| ------------ | ---------------------- | --------------------------------------------------------- | ---------------------------- |
| QA (default) | `{APP_URL}`            | Email: `{TEST_ACCOUNT_EMAIL}` / `{TEST_ACCOUNT_PASSWORD}` | Default for all on-demand QA |
| Production   | `{APP_PRODUCTION_URL}` | As configured                                             | Only when explicitly asked   |

If the user doesn't specify, default to QA environment.

## Test Suite Structure

Test cases live in `skills/qa-on-demand/suites/`:

```
suites/
├── onboarding.json          # Signup, agent creation, first message
├── agents.json              # Agent CRUD, templates, switching
├── chat.json                # Messaging, streaming, file upload, sessions
├── skills.json              # Skill CRUD, scoping, preview
├── scheduled-tasks.json     # Task CRUD, cron, run now
├── files.json               # File browser, upload, workspace
├── memory.json              # Memory page, file access
├── settings.json            # Agent config, gateway, model picker
├── billing.json             # Stripe, subscriptions, credits, plans
├── analytics.json           # PostHog events
├── channels/
│   ├── slack.json           # Full Slack E2E
│   ├── discord.json         # Discord setup and messaging
│   ├── telegram.json        # Telegram bot setup
│   └── whatsapp.json        # WhatsApp QR flow
├── infrastructure.json      # Gateway, workspaces, config sync
├── security.json            # Auth boundaries, route protection
└── cross-cutting.json       # Mobile responsive, error handling, performance
```

## Execution Flow

### Step 1: Determine Scope (Main Agent — You)

Parse the user's request:

- "Full QA" / "test everything" / "regression" → load ALL suite files
- "Test Slack" → load `suites/channels/slack.json`
- "Test billing and onboarding" → load `suites/billing.json` + `suites/onboarding.json`
- "Smoke test" → load only HIGH priority tests from all suites

### Step 2: Load Knowledge Base Context (Main Agent)

Before testing, load relevant knowledge base docs:

1. Read `{KNOWLEDGEBASE_PATH}/README.md` (index)
2. For each area being tested, load the corresponding platform doc
3. Check `{KNOWLEDGEBASE_PATH}/bugs/known-issues.md` — skip known bugs or verify fixes
4. Check `{KNOWLEDGEBASE_PATH}/bugs/patterns.md` — watch for recurring patterns

### Step 3: Environment Setup (Main Agent)

1. Verify target environment is accessible:

   ```bash
   curl -sf {API_URL}/health || echo "API DOWN"
   curl -sf {APP_URL} -o /dev/null || echo "FRONTEND DOWN"
   ```

2. Top up QA credits (QA environment only):

   ```bash
   mongosh "$MONGO_URI" --quiet --eval "
     const user = db.users.findOne({email: '{TEST_ACCOUNT_EMAIL}'});
     db.customers.updateOne({_id: user.customer}, {\$set: {credits: 50000}});
   "
   ```

3. Ensure workspace pool has capacity:
   ```bash
   curl -X PUT {WORKSPACE_CONTROLLER_URL}/api/workspace/pool-size \
     -H "Content-Type: application/json" -d '{"poolSize": 1}'
   ```

### Step 4: Package & Spawn Manager (Main Agent)

Create the run:

```bash
RUN_ID=$(date +%Y%m%d-%H%M%S)
TEST_DIR="tests/on-demand-${RUN_ID}"
mkdir -p "${TEST_DIR}/screenshots"
```

Assemble the Manager's task prompt with:

- Full test checklist (all test cases from the loaded suite files)
- Target URL and credentials
- Run ID
- S3 config (see `references/s3-config.md`)
- Report template reference (see `references/report-template.md`)

Spawn the Manager:

```
sessions_spawn(
  mode: "session",              # persistent — survives across executor rounds
  task: <assembled prompt>,     # includes all test cases, environment, config
  runTimeoutSeconds: 3600       # 1 hour for full run
)
```

See `references/manager-prompt.md` for the full Manager prompt template.

### Step 5: Manager Orchestrates Executors

The Manager (persistent session) does the following:

1. **Creates tracker file** — `qa-tracker-{runId}.md` with all tests as PENDING
2. **Plans batches** — groups 3-5 related tests per Executor batch
3. **Spawns Executors** one at a time (or parallel for independent areas):
   ```
   sessions_spawn(
     mode: "run",                    # one-shot execution
     task: <executor prompt>,        # 3-5 test cases + login + screenshot rules
     runTimeoutSeconds: 900          # 15 min max per batch
   )
   ```
4. **After each Executor returns** — updates tracker with results, spawns next batch
5. **Handles failures** — timeout/crash → mark tests BLOCKED, continue with next batch
6. **Builds HTML report** when all tests complete
7. **Uploads to S3** and returns results + report URL

See `references/executor-prompt.md` for the Executor prompt template.

### Step 6: Receive Results & Deliver (Main Agent)

When Manager completes:

1. Get the report URL + results summary
2. Send to the user (report link + pass/fail counts)
3. Update knowledge base with new bugs/patterns found
4. Log to daily memory file

## Manager Agent Details

The Manager is a **persistent session** (`mode: "session"`) that:

- Never tests anything itself — only orchestrates Executors
- Maintains a tracker file as persistent state (survives across executor rounds)
- Keeps spawning Executors until ALL test cases have a result (PASS/FAIL/BLOCKED/SKIP)
- Builds the final HTML report with embedded screenshots

### Tracker File Structure

```markdown
# QA Tracker: {run-id}

## Meta

- Target: {app URL}
- Account: {email}
- Started: {timestamp}
- Status: In Progress | Complete
- Progress: {X}/{total} tests ({percentage}%)

## Test Cases

| ID        | Test Name              | Status  | Notes                   | Screenshots   |
| --------- | ---------------------- | ------- | ----------------------- | ------------- |
| SLACK-001 | Slack setup form loads | ✅ PASS | Form loads correctly    | 3 screenshots |
| SLACK-002 | Copy manifest          | ❌ FAIL | Clipboard not populated | 2 screenshots |
```

### Batch Sizing

- **3-5 test cases per Executor** — keeps screenshot context manageable
- Each screenshot ~200-500KB base64 in context
- 5 tests × 4-10 screenshots = 20-50 screenshots per batch
- Independent areas can run in parallel batches

## Executor Agent Details

Executors are **one-shot** (`mode: "run"`) sub-agents that:

- Log into the target app
- Run each assigned test case using the `browser` tool
- Take screenshots (minimum 4 per test, save to disk)
- Visually verify screenshots before marking pass/fail
- Return structured JSON results

### Executor Rules

- Run EVERY assigned test. Do NOT skip any.
- Take 4-10 screenshots per test.
- Use the `browser` tool (snapshot + act), NOT Playwright or external automation.
- Visually verify every screenshot with the `image` tool.
- If environment is broken after first test, mark remaining as BLOCKED.
- Return structured results so Manager can parse them.

## Parallel Execution

For independent areas, Manager can run Executors in parallel using different test accounts:

- Slot 0: `{TEST_ACCOUNT_EMAIL}` / `{TEST_ACCOUNT_PASSWORD}`
- Slot 1: Additional test accounts as needed (e.g., `{email}+1`)
- Slot 2: Additional test accounts as needed (e.g., `{email}+2`)

**Critical:** The platform may NOT support multiple concurrent sessions for the same user
account. Each parallel Executor MUST use a different test account.

Pre-register additional test accounts via MongoDB if they don't exist.

## Test Data Seeding

Some areas need pre-existing data. Seed before testing:

| Area            | What to seed                                                       |
| --------------- | ------------------------------------------------------------------ |
| Chat            | At least 2 chat sessions with messages                             |
| Files           | At least 1 uploaded file                                           |
| Skills          | At least 1 custom skill                                            |
| Scheduled Tasks | At least 2 tasks                                                   |
| Channels        | At least 1 connected channel (or test connection as part of suite) |
| Billing         | QA credits topped up to 50000                                      |

## Error Handling

- **Executor timeout (15 min):** Manager marks affected tests as BLOCKED, spawns next batch
- **Executor crash:** Same as timeout — mark BLOCKED, continue
- **>50% BLOCKED in an area:** Skip remaining tests in that area (environment problem)
- **Login failure:** Abort entire run
- **Never mark PASS without screenshot verification**

## Reference Files

- `references/manager-prompt.md` — Full prompt template for the Manager agent
- `references/executor-prompt.md` — Full prompt template for Executor agents
- `references/report-template.md` — HTML report structure and template
- `references/s3-config.md` — S3 upload configuration

## Key Differences from Ticket QA

| Aspect       | Ticket QA (qa-flow)         | On-Demand QA (this skill)    |
| ------------ | --------------------------- | ---------------------------- |
| Trigger      | Linear ticket / PR          | User says "test X"           |
| Queue        | Required (one at a time)    | Not used                     |
| Linear       | Reads ticket, posts results | No Linear interaction        |
| Deploy       | Deploys specific branch     | Tests what's already running |
| Scope        | Single feature/fix          | Full platform or area(s)     |
| Test source  | Generated per-ticket plan   | Master test suite files      |
| Architecture | Single agent                | Manager/Executor pattern     |

## Quick Reference

| Setting                  | Value                                                    |
| ------------------------ | -------------------------------------------------------- |
| Default target           | `{APP_URL}`                                              |
| Test account             | `{TEST_ACCOUNT_EMAIL}` / `{TEST_ACCOUNT_PASSWORD}`       |
| Suites location          | `skills/qa-on-demand/suites/`                            |
| Tests per Executor batch | 3-5                                                      |
| Executor timeout         | 900s (15 min)                                            |
| Manager timeout          | 3600s (1 hour)                                           |
| Screenshots per test     | 4-10                                                     |
| Report output            | `reports/qa-on-demand-{run-id}.html`                     |
| S3 bucket                | `{S3_PUBLIC_BUCKET}`                                     |
| S3 prefix                | `{S3_REPORTS_PREFIX}`                                    |
| MongoDB                  | `get_credential(service="{MONGODB_CREDENTIAL_SERVICE}")` |
| API SSH                  | `ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP}`      |

## Full Environment Access

Same as ticket QA — full admin on QA cloud account. SSH, MongoDB, Redis, S3, EC2, ECR.
See `skills/qa-flow/SKILL.md` for the full infrastructure reference.
