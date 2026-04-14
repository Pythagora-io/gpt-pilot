---
name: qa-phase2
description: >-
  Phase 2: Review and Expand Testing Plan. Use after Phase 1 is finished. Review the qa-phase0 testing plan with fresh context from phase 1. Generate bug hypotheses and expand the plan with additional test cases. Never shorten the plan.
---

# Phase 2: Review & Expand Testing Plan

**Goal:** Review the existing testing plan with the knowledge gained from Phase 1
(PR diff, code changes, environment state). Generate bug hypotheses and expand the
plan if needed. **Never make the plan shorter — only add.**

## Hard Rules

1. **Use the `browser` tool for all browser automation.** Use the built-in `browser` tool (snapshot + act) in **headed mode** (not headless). Do NOT use Playwright, `browser_use`, or any external browser automation library.
2. **Test environments: QA/staging or production ONLY.** Never localhost. Never worktrees.
3. **Never remove test cases from the qa-phase0 plan.** Only add. The qa-phase0 plan is the baseline contract.

## Prerequisites

- Phase 1 completed — environment verified, PR understood
- Testing plan exists at `{testFolder}/testing-plan.md` AND `{testFolder}/test-cases.json`

## Workflow

### 2.1 Re-Read the Testing Plan

Read both `{testFolder}/testing-plan.md` and `{testFolder}/test-cases.json`. Understand
every test case (API and browser), its priority, and its steps.

### 2.2 Load Cross-Cutting Test Strategies

Based on the change type (from Phase 1), load relevant strategies from `{KNOWLEDGEBASE_PATH}/test-strategies/`:

| Change type           | Load                                                                        |
| --------------------- | --------------------------------------------------------------------------- |
| UI changes            | `test-strategies/mobile-responsive.md`, `test-strategies/error-handling.md` |
| State/persistence     | `test-strategies/state-persistence.md`                                      |
| Concurrent operations | `test-strategies/race-conditions.md`                                        |
| Auth/permissions      | `test-strategies/auth-boundaries.md`                                        |
| Pricing/locale        | `test-strategies/geo-location.md`                                           |
| Performance-critical  | `test-strategies/performance.md`                                            |

### 2.3 Generate Bug Hypotheses

Think adversarially. Combine PR analysis with knowledge base:

**What could go wrong? (from PR analysis)**

- Edge cases the developer probably missed?
- Empty inputs, special characters, concurrent access?
- Integration points that could fail?
- Race conditions?

**What has gone wrong before? (from knowledge base)**

- Check `bugs/patterns.md` — does this change touch recurring patterns?
  - State persistence → atomic writes?
  - Name/slug handling → special characters?
  - Auth flows → failure handling?
  - Text inputs → whitespace trimming?
  - Config changes → drift?
- Check relevant `platform/*.md` — historical issues documented?

**What's NOT tested by the developer?**

- Read PR's "What you did NOT verify" section
- Code paths with no unit tests
- Error handling that's just `catch {}`

**What are hidden dependencies?**

- Code path A assumes B already ran?
- Frontend assumes backend method exists?
- Feature works via one entry point but not another?

**What's the blast radius?**

- Could this break existing features?
- Shared modules other code depends on?

### 2.4 Expand the Testing Plan

Based on hypotheses, **add** test cases to `{testFolder}/test-cases.json` ONLY.
`testing-plan.md` is write-once (created in phase 0) and must NOT be modified.

- New API tests → add to `apiTests` array in JSON (use `API-X.Y` IDs)
- New browser tests → add to `browserTests` array in JSON (use `PW-X.Y` IDs)
- New edge cases discovered from PR analysis
- Test patterns from knowledge base strategies
- Regression tests for nearby functionality
- Any gaps identified in the existing plan

**Rules:**

- Keep the same format (API-X.Y / PW-X.Y, priority, steps, expected, status)
- Add new tests at the end of each section
- Mark all new tests as `"PENDING"` in JSON
- Do NOT change existing test case IDs, steps, or priorities
- Do NOT remove any existing test cases
- **Both sections must have tests.** If the expansion is backend-heavy, still add browser
  smoke tests. If frontend-heavy, still add API verification tests.

If knowledge base checklists exist for the feature area, cross-reference and add any missing edge cases.

### 2.5 Update Plan Meta

Update the status in `test-cases.json` only (`testing-plan.md` is write-once):

```json
{ "meta": { "status": "PHASE2" } }
```

### 2.6 Share the Plan

Print the complete testing plan to the conversation so the team can review before execution begins.

### 2.7 Update Queue & Transition

```bash
python3 skills/qa-queue/queue.py update-phase \
  --phase phase2-done \
  --notes "Testing plan reviewed and expanded. N total test cases (X HIGH, Y NORMAL). Added M new tests."
```

Proceed to `qa-phase3`.

## Output

- `test-cases.json` expanded with new tests (never shortened). `testing-plan.md` unchanged (write-once).
- Bug hypotheses documented
- Both API and browser test sections have tests
- Plan shared with team for review
- Ready for execution
