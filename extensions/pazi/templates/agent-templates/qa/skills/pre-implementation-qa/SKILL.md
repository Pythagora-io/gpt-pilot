---
name: pre-implementation-qa
description: >-
  Create a pre-implementation QA testing plan for a feature or task BEFORE it's built.
  Produces an HTML report with detailed, expandable test cases and a test-cases.json file.
  Use when asked to create a testing plan, pre-QA plan, or QA plan for a task/feature
  that hasn't been implemented yet. Does NOT run the queue, deploy, or manage environments.
---

# Pre-Implementation QA

Create a testing plan for a feature/task BEFORE implementation. The output is an HTML
report with expandable test cases and a structured `test-cases.json` file. This skill
is for planning only — no deployment, no queue management, no test execution.

**Before starting:** Read `environment.md` in the template root to resolve all
environment-specific values.

## Hard Rules

1. **Use the `browser` tool for all browser automation.** Use the built-in `browser` tool (snapshot + act) in **headed mode** (not headless). Do NOT use Playwright, `browser_use`, or any external browser automation library.
2. **Never hardcode environment URLs in the plan.** The testing environment varies between runs. Use only relative paths (`/login`, `/dashboard`, `/slack/config-tokens`) in test cases. The execution phase resolves the actual base URL. Never localhost. Never worktrees.
3. **The testing plan is the single source of truth.** Everything downstream depends on it.

## Workflow

### 1. Create Test Folder

Create a dedicated folder for this test plan. All artifacts go here.

```bash
RUN_ID="qa-PAZ-XXX-preqa-$(date +%Y%m%d-%H%M%S)"
TEST_DIR="{WORKSPACE_DIR}/{TEST_RUNS_DIR}/$RUN_ID"
mkdir -p "$TEST_DIR/screenshots"
```

### 2. Load Knowledge Base Context

Load platform knowledge BEFORE analyzing the task:

1. Read `{KNOWLEDGEBASE_PATH}/README.md`
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

### 3. Fetch Ticket/PR Information

**For Linear tickets:**

```bash
# Use the Linear skill to fetch ticket info
python3 skills/linear/scripts/linear_api.py --api-key "$LINEAR_KEY" issue --id "PAZ-XXX"
```

**For PRs (if they exist):**

```bash
gh pr view <number> --repo {GITHUB_ORG}/{PLATFORM_REPO} --json title,body,files,url
gh pr diff <number> --repo {GITHUB_ORG}/{PLATFORM_REPO}
```

Search for companion PRs:

```bash
gh search prs "PAZ-XXX" --owner {GITHUB_ORG} --json url,title,state --limit 5
```

Extract: title, description, files changed, companion PRs, what areas are affected.

### 4. Analyze Existing Code (if applicable)

If the feature touches existing code, explore the current implementation to understand:

- What exists today (current behavior)
- Where the change will likely happen (files, functions)
- What other features might be affected (blast radius)

This informs better test cases — you can't write good edge cases without understanding
the codebase.

### 5. Write the Test Plan

You must create **two files** — a structured JSON file and an HTML report. Both live in `$TEST_DIR`.

#### 5a. Structured Test Plan: `$TEST_DIR/test-cases.json`

This is the machine-readable test plan. It has two mandatory sections: **API tests** and
**browser tests**.

```json
{
  "meta": {
    "id": "PAZ-XXX",
    "runId": "qa-PAZ-XXX-preqa-20260413-010000",
    "environment": "staging",
    "testAccount": {
      "email": "{TEST_ACCOUNT_EMAIL}",
      "password": "{TEST_ACCOUNT_PASSWORD}"
    },
    "date": "2026-04-13",
    "status": "PRE-QA",
    "prerequisites": [
      "Deploy feature branches to the staging environment",
      "Log into the staging environment with the test account",
      "Any other setup needed before testing"
    ]
  },
  "summary": "Short description of what's being tested and why",
  "apiTests": [
    {
      "id": "API-1.1",
      "name": "Configure endpoint accepts valid input",
      "priority": "HIGH",
      "method": "POST",
      "endpoint": "/api/endpoint",
      "headers": { "Content-Type": "application/json" },
      "body": { "key": "value" },
      "curlCommand": "curl -X POST ${API_URL}/endpoint -H 'Cookie: <session>' -H 'Content-Type: application/json' -d '{\"key\":\"value\"}'",
      "expectedStatus": 200,
      "expectedBody": null,
      "assertions": ["response.status === 200", "response.body contains expected field"],
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
      "name": "Feature form defaults to correct state",
      "priority": "HIGH",
      "steps": [
        "Navigate to /login",
        "Log in with test account",
        "Click 'Agent setup' in the left sidebar (gear icon)",
        "Navigate to the specific feature area",
        "Observe the form/UI state"
      ],
      "expected": "Form shows correct default values. Specific field X shows 'Y'.",
      "testInputs": {
        "account": "{TEST_ACCOUNT_EMAIL}",
        "password": "{TEST_ACCOUNT_PASSWORD}",
        "specificValue": "exact value to enter"
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
  status codes, response bodies, auth, error handling.
- **`browserTests`** — Tests that interact with the UI via the `browser` tool. Verify user-visible
  behavior, UI rendering, navigation, forms, visual state.
- **Both sections are MANDATORY.** Every test plan must have API tests AND browser tests.
  If a change is purely backend, still add basic browser smoke tests.
  If a change is purely frontend, still add API tests.
- **`meta.environment`** — Label only (e.g. `"staging"`, `"production"`). Never a URL.
  The actual base URL and API URL are resolved at execution time by the test runner.
- **`meta.prerequisites`** — Array of strings listing what must be true before any test runs.
  Use generic terms ("the staging environment") instead of specific domain names.
- **IDs:** API tests use `API-X.Y`, browser tests use `PW-X.Y`
- **Priority:** `HIGH` or `NORMAL`
- **API test fields:**
  - `curlCommand` — **MANDATORY.** Curl command using `${API_URL}` variable for the base URL.
    Example: `curl -X POST ${API_URL}/slack/config-tokens -H 'Cookie: <session>'`.
    The execution phase substitutes the real URL. Never hardcode a domain name.
- **Browser test fields:**
  - `steps` — **Detailed numbered steps.** Use relative paths (`/login`, `/dashboard`) — never
    full URLs. Each step must be specific enough for someone who has never seen the feature.
  - `expected` — Exact observable outcome with precise text, states, or timing.
  - `testInputs` — **MANDATORY object.** Concrete values used in this test.

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

**Scale with task size:**

- Small (1-3 files likely affected): 5-10 test cases total
- Medium (4-10 files): 10-20 test cases total
- Large (10+ files): 20-40 test cases total

Always at least 3 HIGH and 3 NORMAL priority tests across both sections.

#### 5b. HTML Report

Build an HTML report using the `build-report` skill. The report uses expandable `<details>`
elements for each test case, **all collapsed by default**.

The report must include:

1. **Summary cards** — total API tests, browser tests, categories, total count
2. **Prerequisites section** — what must be true before testing
3. **Risk areas** — key-value table of risks with severity tags
4. **Test cases by category** — each test as a collapsible `<details>` element containing:
   - Test ID + name + priority tag in the `<summary>`
   - Numbered step-by-step execution instructions in the body
   - Expected outcome box
   - curl commands or code for API/bypass tests
5. **Implementation guidance** — callout boxes with technical notes for the developer
6. **Ticket info** — metadata table
7. **Expand All / Collapse All buttons** at the top

Upload to S3:

```bash
aws s3 cp "$TEST_DIR/qa-preqa-report.html" \
  "s3://{S3_PUBLIC_BUCKET}/{S3_REPORTS_PREFIX}$RUN_ID/qa-preqa-report.html" \
  --content-type "text/html" --profile {AWS_PROFILE}
```

Report URL: `{S3_REPORTS_URL_BASE}/$RUN_ID/qa-preqa-report.html`

Save locally too: `$TEST_DIR/qa-preqa-report.html`

### 6. Post to Linear & Reply in Slack

Post a short comment to Linear:

```bash
python3 skills/linear/scripts/linear_api.py --api-key "$LINEAR_KEY" comment \
  --issue-id "PAZ-XXX" \
  --body "## Pre-Implementation QA Plan
Report: <url>
Summary: <1-2 lines about test count and key risk areas>"
```

Reply in the Slack thread where the request came from with:

- Test count summary
- Key risk areas
- Report link

### 7. Handoff

Assign to developer agent, tag in Slack thread:

```
<@{SLACK_DEVELOPER_AGENT_ID}> can you implement this - PAZ-XXX
```

## Key Principles

- **Think like an attacker.** What breaks? What was missed?
- **Be specific.** "Check that it works" is not a test case.
- **Be concrete.** Every step, every input, every expected output — spelled out.
- **Cover all paths.** Happy path + negative path + edge cases. All three, every time.
- **You own production quality.** If a bug slips through your plan, it's on you.
