# Claude Code Implementation Prompt Template

Use this template when launching Claude Code for feature implementation.
Fill in the bracketed placeholders.

---

You are implementing a feature for this project. Read and follow these instructions completely.

## Task

[Paste task.md contents or path]

## Implementation Plan

[Paste the winning plan from the cross-review verdict, or path to the plan file]

## File Changes Required

[List from the verdict — specific files, what changes in each]

## CRITICAL RULES

1. **COMPLETE IMPLEMENTATION**: Implement EVERY feature in the plan. No stubs. No TODOs. No "left as exercise". Every button works. Every endpoint is functional. Every UI element renders.

2. **ZERO BUGS**: Test everything you build. If it doesn't work, fix it before moving on. Do not declare completion with known issues.

3. **TEST-DRIVEN (backend only)**:
   - Write tests for API endpoints, data logic, utility functions
   - Do NOT write tests for React components or frontend UI
   - Run the project's test command (e.g. `npm test`)
   - ALL tests must pass before declaring done

4. **VERIFY YOUR WORK COMPILES AND PASSES CHECKS**: After implementing:
   - Run the TypeScript compiler: `npx tsc --noEmit`
   - Run ESLint: `npx eslint . --ext .ts,.tsx`
   - Run backend tests with the project's test command
   - Do NOT start any local dev servers — worktrees are code-only
   - Check for leftover TODOs/FIXMEs and resolve them
   - If any check fails, fix the code before declaring done

5. **DO NOT COMMIT UNTIL CHECKS PASS**: Do NOT make any git commits until you have:
   - Implemented everything
   - TypeScript compiles cleanly
   - ESLint passes
   - Backend tests pass
   - Fixed any issues found
     Only after ALL of the above pass, make a single commit (or a few atomic commits). Use conventional format: `feat:`, `fix:`, `test:`, `refactor:`

6. **STAY IN SCOPE**: Only modify files related to this feature. Shared utilities are OK if needed.

7. **FIX BLOCKING BUGS**: If existing code has a bug that blocks your feature, fix it and note it in the commit.

## Codebase Locations

- Main repo: [worktree path]
- Agent repo: [worktree path, if applicable]

## Tech Stack Reference

- Frontend: React + TypeScript + Vite + Tailwind + shadcn/ui
- Backend: Node.js + Express + TypeScript + MongoDB (Mongoose)
- NOTE: Do NOT start local dev servers. Worktrees are code-only.
- State: React hooks + context
- Auth: [Describe the project's auth mechanism]
- Routing: React Router v6
