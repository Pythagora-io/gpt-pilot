---
name: development
description: Core development workflow rules. Enforces bug-fixing discipline, cross-package awareness, and quality standards during implementation. This skill is always active during development tasks.
---

# Development Workflow

## Bug-Fixing Discipline (MANDATORY)

1. **Fix ALL bugs you encounter** — If you discover a bug during development, testing, or code review, you MUST fix it. Do not dismiss issues as "out of scope", "pre-existing", or "unrelated". If you found it, you own it.

2. **Cross-package bugs are your responsibility** — If a frontend change reveals a backend bug (or vice versa), fix it in the appropriate package. Do not limit yourself to a single package boundary when the fix is clear.

3. **Never ignore failing behavior** — If something doesn't work as expected after your changes, investigate and fix it before considering your task complete. This includes:
   - API responses returning incorrect data
   - UI not reflecting saved state after refresh
   - Data format mismatches between frontend and backend
   - Broken flows that depend on the code you touched

4. **Ask before skipping** — If a bug is genuinely outside your ability to fix (e.g., third-party service issue, requires credentials you don't have, needs architectural decision), explicitly ask the user rather than silently moving on. Never assume the user wants you to ignore a problem.

## Completeness (MANDATORY)

1. **Implement EVERYTHING** — Every feature in the plan must be fully implemented. No stubs, no TODOs, no "will add later". Every button must work. Every endpoint must be functional. Every UI element must render correctly.

2. **Never leave bugs** — The final code must be bug-free. If something doesn't work, fix it before moving on. Do not declare implementation complete with known issues.

3. **Test-Driven Development (backend only)**:
   - Write tests for API endpoints, data logic, and utility functions
   - Do NOT write tests for React components or frontend UI
   - Run tests with the project's test command (e.g. `npm test`)
   - ALL tests MUST pass before declaring implementation complete
   - If a test fails, fix the code or the test until it passes

4. **Verify your work compiles and passes checks** — After implementing:
   - Run the TypeScript compiler: `npx tsc --noEmit`
   - Run ESLint: `npx eslint . --ext .ts,.tsx`
   - Run backend tests with the project's test command
   - Do NOT start any local dev servers — worktrees are code-only
   - Check for leftover TODOs/FIXMEs and resolve them

5. **Never silently swallow errors** — All user-facing async operations MUST have error handling:
   - Never use `void asyncFn()` without a `.catch()` — unhandled promise rejections hide bugs
   - RPC/API calls that fail should show feedback to the user (toast, alert, error state)
   - If a dialog closes after an action, the action must have succeeded — don't close the dialog before confirming success
   - Add console logging for debugging RPC calls (params sent, result received, errors)

## Commit Discipline (MANDATORY)

1. **HUSKY PRE-COMMIT HOOK MUST BE ACTIVE** — Before making any commit, verify husky is set up:
   - Run `npx husky` in the repo root if unsure
   - The pre-commit hook runs `lint-staged` (ESLint + Prettier) then `npm run typecheck`
   - If a commit goes through without the hook running (no lint/typecheck output), STOP and fix husky first
   - Never use `--no-verify` to bypass the hook
2. **DO NOT COMMIT until QA passes** — Do NOT make any git commits until:
   - All code is implemented (no stubs, no TODOs)
   - Backend tests pass
   - TypeScript compiles cleanly (`npx tsc --noEmit`)
   - Feature works end-to-end in the browser
   - All QA scenarios from the plan have been manually verified
   - All bugs found during testing are fixed
3. **Only commit clean, tested code** — After all checks pass, make a single commit (or a few atomic commits). Never commit code that has known failures.
4. **Use conventional commits**: `feat:`, `fix:`, `test:`, `refactor:`

## Implementation Standards

1. **Read before writing** — Always read existing code before modifying it. Understand the patterns in use.
2. **Follow existing patterns** — When a codebase already handles a case (e.g., data URI stripping in onboarding), apply the same pattern in new code that does the same thing.
3. **Verify your changes work** — After making changes, verify they solve the problem. If you can run the code or tests, do so.
4. **Minimal, focused changes** — Only change what needs to change. Don't refactor surrounding code, add unnecessary abstractions, or "improve" unrelated code.
