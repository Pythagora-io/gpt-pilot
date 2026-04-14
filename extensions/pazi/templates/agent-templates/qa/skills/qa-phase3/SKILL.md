---
name: qa-phase3
description: >-
  Phase 3: Execute Tests. Use after Phase 2 is finished. Run ALL test cases from test-cases.json - both API tests and browser tests. Update the JSON continuously as each test completes. Take screenshots as evidence.
---

# Phase 3: Execute Tests

**Goal:** Run every test case from `test-cases.json`. Both **API tests** and **browser
tests** must be executed - they are separate sections and both are required. Update the
JSON in real-time as each test completes.

**Before starting:** Read `environment.md` in the template root to resolve all
environment-specific values.

## Hard Rules

1. **Use the `browser` tool for all browser automation.** Use the built-in `browser` tool (snapshot + act) in **headed mode** (not headless). Do NOT use Playwright, `browser_use`, or any external browser automation library.
2. **Test environments: QA/staging or production ONLY.** Never localhost. Never worktrees.
3. **Update test-cases.json after EVERY test.** Status, notes, screenshots, errors - immediately.
   **Do NOT modify `testing-plan.md`.** It is the original plan and stays unchanged. Only `test-cases.json` gets updated.
4. **Run ALL tests in BOTH sections.** API tests AND browser tests. Do not skip, do not stop early.
5. **HIGH priority first within each section.** Execute all HIGH tests before NORMAL in each section.
6. **Run API tests first, then browser tests.** API tests are faster and catch backend issues early.
7. **⚠️ CRITICAL: Visually verify EVERY screenshot BEFORE marking pass/fail.** After taking a screenshot, you MUST analyze it (using the `image` tool or by checking the browser snapshot) BEFORE writing the test result. Do NOT mark a test as PASS based solely on action success - the screenshot is ground truth. If the screenshot shows a 404 page, error page, wrong page, or broken UI, the test FAILS even if the browser action didn't throw an error. Common false-pass patterns:
   - Navigation "succeeds" but page is a 404
   - Page loads but shows login/signup instead of expected content
   - Element exists in snapshot but page shows error states
   - Action completes but the result is wrong

   **If you skip screenshot verification and mark PASS on a broken page, the entire test run is invalid.**

8. **Top up QA credits before testing.** Before running any browser tests, ensure the QA test account has sufficient credits. Check the relevant database collection/table for credits and top up as needed before testing.

## Full Environment Access

You have **full access to the entire cloud account** used for the QA environment. This
environment exists solely for testing - there is nothing you can break that matters. During
test execution, do whatever is needed to properly test each scenario:

- **MongoDB:** Add credits to test billing flows, create users for multi-user tests, change plans, seed specific data states, reset collections between tests
- **Agents & Workspaces:** Create test agents, configure them with specific settings, create workspaces, delete old test data
- **Redis:** Check cache state, flush keys if tests need clean state, verify pub/sub
- **EC2 instances:** SSH in for logs, restart containers if environment gets stuck, check resource usage
- **S3:** Upload test files, verify file storage, clean up test artifacts
- **Stripe (test mode):** Create test subscriptions, trigger webhook events, set up billing scenarios

Do not hesitate or ask permission - the entire environment is your testing sandbox.
If a test case requires specific data (credits, agents, plan type, etc.), set it up yourself.

## Prerequisites

- Phase 2 completed - testing plan reviewed and expanded
- `{testFolder}/test-cases.json` exists with both `apiTests` and `browserTests` sections
- `{testFolder}/testing-plan.md` exists (human-readable companion)

**If `test-cases.json` does not exist → STOP. Go back to `qa-phase0` and create it.**
Do not proceed without it. Do not improvise tests from the markdown plan alone.
The JSON is the source of truth for execution.

## Workflow

### 3.1 Setup

```bash
# Create screenshots directories
mkdir -p {testFolder}/screenshots
```

Read `{testFolder}/test-cases.json` - this is the file you follow and update during execution.

### 3.2 Execute API Tests FIRST

Run all tests from the `apiTests` section of `test-cases.json`. HIGH priority first, then NORMAL.

**For each API test:**

1. **Update status** in `test-cases.json`: `"PENDING"` → `"RUNNING"`
2. **Execute the API call** using curl or Python requests:
   ```bash
   curl -sf -X {method} {API_URL}{endpoint} \
     -H "Content-Type: application/json" \
     -H "Cookie: {auth-cookie}" \
     -d '{body}'
   ```
3. **Check assertions** - verify status code, response body, headers
4. **Update test-cases.json immediately** with:
   - `"status"`: `"PASS"`, `"FAIL"`, `"BLOCKED"`, or `"NEED_HELP"`
   - `"actualStatus"`: the HTTP status code received
   - `"actualBody"`: the response body (or relevant excerpt)
   - `"notes"`: what you observed
   - `"error"`: error message if failed
5. **Move to next API test**

**If a critical API test fails (e.g. login, health check), investigate immediately** -
browser tests will likely fail too if the backend is broken.

### 3.3 Execute Browser Tests

After API tests, run all tests from the `browserTests` section. HIGH priority first, then NORMAL.

**How to use the `browser` tool:**

- `browser action=open url=<url>` - open a URL
- `browser action=snapshot` - get the page DOM tree with element refs
- `browser action=screenshot` - take a PNG screenshot
- `browser action=act kind=click ref=<ref>` - click an element
- `browser action=act kind=type ref=<ref> text=<text>` - type into an element
- `browser action=act kind=press key=<key>` - press a key
- `browser action=act kind=fill ref=<ref> text=<text>` - fill a form field
- Use `snapshot` to find element refs, then `act` to interact with them.
- After each significant action, take a `screenshot` and/or `snapshot` to verify state.

**QA environment login:**

1. `browser action=open url="{APP_URL}/login"`
2. Snapshot, find "Continue with Email" button, click it
3. Fill email `{TEST_ACCOUNT_EMAIL}`, fill password `{TEST_ACCOUNT_PASSWORD}`, click login
4. Wait for dashboard to load (snapshot to verify)

**For each browser test:**

1. **Update status** in `test-cases.json`: `"PENDING"` → `"RUNNING"`
2. **Execute the steps** exactly as written - as a real user would, using the `browser` tool
3. **Take screenshots** at key moments and **SAVE THEM TO DISK**.
   Every browser test MUST have at least one saved screenshot file.

   **HOW TO SAVE:** The `browser action=screenshot` returns the image inline.
   You MUST then write it to a file. Two methods:

   **Method A (preferred):** Use the browser tool's built-in file save:

   ```
   browser(action="screenshot", path="{testFolder}/screenshots/{PW-id}-NNN-description.png")
   ```

   **Method B (fallback):** Screenshot first, then use `exec` to copy:

   ```
   browser(action="screenshot")  // returns image
   exec: cp /tmp/last-screenshot.png {testFolder}/screenshots/{PW-id}-NNN-description.png
   ```

   **A test with zero screenshot FILES ON DISK is INVALID. Phase 4 will reject it.**

   Take screenshots at:
   - Initial state before the action
   - Action being performed (button clicked, form filled)
   - Result (success message, error dialog, changed state)
   - Any unexpected behavior

4. **Save screenshots** as: `{testFolder}/screenshots/{PW-id}/NNN-description.png`
5. **⚠️ MANDATORY: Verify screenshots before marking result.**
   Use the `image` tool to analyze each screenshot you just took. Check for:
   - 404 pages, error pages, blank screens
   - Error banners, warnings, "out of credits" messages
   - Wrong page loaded (login page when expecting dashboard, etc.)
   - Broken layouts, missing content, unexpected UI state

   The screenshot is ground truth. If it shows something wrong, the test FAILS
   regardless of whether the browser actions appeared to succeed.

   Write `screenshotVerification` with a brief description of what each screenshot shows.

   Then set `screenshotMatchesExpected` to `true` or `false`:
   - `true` — the screenshot shows exactly what the test's `expected` field describes
   - `false` — the screenshot shows something different from what was expected

   **HARD RULE: If `screenshotMatchesExpected` is `false`, the test status MUST be `FAIL`.**
   No exceptions. Do not rationalize with DB queries, API calls, code review, or "it worked
   in a previous test run." The screenshot is what the user sees.

6. **Update test-cases.json immediately** with:
   - `"status"`: `"PASS"`, `"FAIL"`, `"BLOCKED"`, or `"NEED_HELP"`
   - `"screenshots"`: array of screenshot file paths
   - `"screenshotVerification"`: what each screenshot actually shows
   - `"screenshotMatchesExpected"`: `true` or `false`
   - `"notes"`: what you observed, any deviations from expected behavior
   - `"error"`: error message if failed
7. **Move to next browser test**

**Do NOT update `testing-plan.md`.** It is the original plan and must stay unchanged.
`test-cases.json` is the only file that gets updated with results during testing.

### 3.3 Screenshot Rules

- **Quality over quantity.** 2-4 well-chosen screenshots per test that prove something.
- Each screenshot should tell a story - if you can't explain why it matters, don't take it.
- Save as: `{testFolder}/screenshots/{TC-id}/NNN-description.png`

### 3.3b Screenshot Auto-Save Location

The `browser action=screenshot` tool **automatically saves every screenshot to disk** at:

```
~/.openclaw/media/browser/<uuid>.png
```

Files are named with random UUIDs and sorted by modification time. After completing
all browser tests, collect these screenshots and copy them to the test folder with
meaningful names:

```bash
# List screenshots from this test run (check timestamps)
ls -lt ~/.openclaw/media/browser/*.png | head -30

# Copy and rename to test folder (map chronological order to test cases)
cp ~/.openclaw/media/browser/<uuid>.png {testFolder}/screenshots/01-PW-1.1-login-page.png
```

**This is MANDATORY.** Every test run must end with named screenshots in
`{testFolder}/screenshots/` collected from `~/.openclaw/media/browser/`.
Phase 4 will upload these to S3 and embed them in the HTML report.

**Tip:** Note the timestamp before starting browser tests so you can filter
screenshots from this run vs older ones:

```bash
TEST_START=$(date +%s)
# ... run tests ...
# After tests, find screenshots from this run:
find ~/.openclaw/media/browser/ -name '*.png' -newer /tmp/test-start-marker -type f | sort
```

### 3.4 Investigating Failures

When a test fails:

1. **Retry once** to rule out flakiness
2. **Check logs:**
   - `ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP} 'docker logs {API_CONTAINER_NAME} --tail 200 2>&1 | grep -iE "error|fail" | head -20'`
3. **Check database** if the bug involves data:
   - MongoDB via `get_credential(service="{MONGODB_CREDENTIAL_SERVICE}")`
4. **Check browser console** for JS errors
5. **Document everything** in the test case's Notes field:
   - Error messages, log excerpts, DB state
   - Root cause hypothesis
   - Steps to reproduce the failure

**Do NOT stop testing to investigate at length.** Mark the test as `❌ FAIL` with notes,
continue to the next test. Deep investigation happens after all tests complete.

### 3.5 Spawning Sub-Agents for Large Plans

For testing plans with 10+ test cases, spawn sub-agents to run batches:

- Batch 3-5 related tests per sub-agent
- Set `runTimeoutSeconds: 900` (15 minutes max)
- Each sub-agent: login via browser tool → execute tests → take screenshots → write results
- After each sub-agent completes, update the main testing plan with results
- **Never run parallel sub-agents** - one at a time (they share the test account and browser)

### 3.6 Crash Recovery

If testing stops or crashes mid-way:

1. `test-cases.json` has the current state of every test (PASS/FAIL/PENDING) in both sections
2. The queue has `phase: "phase3"` and notes about progress
3. **To resume:** Read `test-cases.json`, find the first `"PENDING"` test in each section, continue from there
4. Do NOT re-run tests that already have `"PASS"` or `"FAIL"` status

Update queue after every batch of tests:

```json
{
  "phase": "phase3",
  "lastPhaseUpdate": "<now>",
  "notes": "API: 5/5 done (5 pass). Browser: 3/10 done (2 pass, 1 fail PW-1.4). Continuing..."
}
```

### 3.7 Completion Check

After executing all tests in BOTH sections, verify:

- **Zero API tests are `"PENDING"`** - every API test has a result
- **Zero browser tests are `"PENDING"`** - every browser test has a result
- **Every browser test has `screenshotVerification` filled in** — proof the screenshot was checked
- **Every `"FAIL"` has notes** explaining what happened
- **Every browser test has at least one screenshot file** in `{testFolder}/screenshots/{PW-id}/`
- **Every browser test has a non-empty `screenshots` array** in test-cases.json with actual file paths
- **Every browser test has `screenshotMatchesExpected` set to `true` or `false`** (not `null`)
- **No browser test has `screenshotMatchesExpected: false` with `status: "PASS"`** — if you find one, flip it to FAIL immediately
- **Every `"BLOCKED"` has a reason** documented

If any test in either section is still PENDING, you are NOT done. Keep going.
If any browser test has `status` set but `screenshotVerification` is empty or `screenshots` array is empty, the result is invalid — go back and take/verify the screenshots.

### 3.8 Update Queue & Transition

```bash
python3 skills/qa-queue/queue.py update-phase \
  --phase phase3-done \
  --notes "All tests done. API: X/Y pass. Browser: A/B pass. C fail, D blocked."
```

Proceed to `qa-phase4`.

## Quick Reference

| Setting              | Value                                                                                           |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| QA Frontend          | `{APP_URL}`                                                                                     |
| QA API               | `{API_URL}`                                                                                     |
| Test account         | `{TEST_ACCOUNT_EMAIL}` / `{TEST_ACCOUNT_PASSWORD}`                                              |
| Screenshots          | `{testFolder}/screenshots/{TC-id}/NNN-description.png`                                          |
| Sub-agent timeout    | 900s (15 minutes)                                                                               |
| Sub-agent batch size | 3-5 tests                                                                                       |
| API logs             | `ssh -i {SSH_KEY_PATH} {SSH_USER_EC2}@{API_EC2_IP} 'docker logs {API_CONTAINER_NAME} --tail N'` |
| MongoDB              | Via `get_credential(service="{MONGODB_CREDENTIAL_SERVICE}")`                                    |
