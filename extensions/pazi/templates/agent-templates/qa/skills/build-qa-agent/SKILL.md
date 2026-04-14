---
name: build-qa-agent
description: >-
  Interactive setup wizard that guides the user through configuring a QA agent from
  the template. Walks through: GitHub access, optional Linear access, repo analysis,
  architecture understanding, infrastructure discovery, and filling in environment.md.
  Use when: setting up a new QA agent, onboarding QA for a new project, or when someone
  says "set up QA", "build a QA agent", "configure QA testing".
---

# Build QA Agent — Interactive Setup Wizard

Guide the user step-by-step through setting up a fully configured QA agent. By the end,
`environment.md` will be populated with all the values the QA skills need, and the agent
will have deep knowledge of the codebase it's testing.

## Philosophy

- _Conversational, not interrogative._ Don't dump a wall of questions. One step at a time.
- _Discover before asking._ If you can figure something out from the repo, don't ask.
- _Be transparent._ Tell the user what you're doing and why at each step.
- _Progressively fill `environment.md`._ Update it as you learn things, not all at once.
- _Adapt._ Not every project has all these components. Skip what doesn't apply.

## Setup Flow

```
Step 1: GitHub Access            ← REQUIRED
Step 2: Linear Access            ← OPTIONAL
Step 3: Clone & Analyze Repos    ← Automatic
Step 4: Build Knowledge Base     ← Automatic
Step 5: Infrastructure Discovery ← Conversational
Step 6: Test Account Setup       ← Conversational
Step 7: Integrations & Team      ← Conversational
Step 8: Validation               ← Automatic
```

---

## Step 1: GitHub Access (REQUIRED)

**Goal:** Get read access to the project's repositories.

Ask the user:

> I need access to your GitHub repos to understand what I'll be testing. Can you give
> me a GitHub personal access token with `repo` scope? I'll use it to clone and analyze
> your codebase.

Use `ask_for_credentials`:

```
ask_for_credentials(
  service: "GitHub",
  fields: ["personal_access_token"],
  message: "I need a GitHub personal access token (PAT) with 'repo' scope to clone and analyze your repositories. You can create one at https://github.com/settings/tokens"
)
```

After receiving the token:

1. Save it: `save_credential(service="github", type="token", key=<token>)`
2. Configure git: `gh auth login --with-token <<< "<token>"`
3. Ask which repos to analyze:
   > Which repositories should I be testing? Give me the org/repo names
   > (e.g., `acme/backend`, `acme/frontend`). I'll clone them and figure out how
   > everything fits together.

Accept one or more repos. The first one listed is treated as the primary platform repo.

**Update `environment.md`:**

- `GITHUB_ORG` — extracted from repo names
- `PLATFORM_REPO` — first repo name
- `AGENT_REPO` — second repo name (if provided, otherwise leave blank)

---

## Step 2: Linear Access (OPTIONAL)

**Goal:** Connect to Linear for ticket-driven QA workflows.

Ask:

> Do you use Linear for project management? If so, I can integrate with it to
> automatically pick up tickets, post QA results, and manage the testing pipeline.
> This is optional — I can do QA without it.

If yes:

```
ask_for_credentials(
  service: "Linear",
  fields: ["api_key"],
  message: "I need a Linear API key. You can create one at https://linear.app/settings/api → 'Personal API keys' → 'Create key'"
)
```

After receiving:

1. Save it: `save_credential(service="linear", type="api_key", key=<key>)`
2. Query Linear to discover:
   ```bash
   # Get team info, workflow states, and users
   curl -s -X POST https://api.linear.app/graphql \
     -H "Authorization: $LINEAR_KEY" \
     -H "Content-Type: application/json" \
     -d '{"query": "{ teams { nodes { id name states { nodes { id name type } } } } viewer { id name } }"}'
   ```
3. Auto-discover and fill:
   - `LINEAR_QA_USER_ID` — the viewer's ID (the agent's own user)
   - `LINEAR_QA_STATE_ID` — find a state named "QA" or "Testing" or similar
   - `LINEAR_TODO_STATE_ID` — find state with type "unstarted" named "Todo"
   - `LINEAR_BLOCKED_STATE_ID` — find state named "Blocked" (if exists)

4. Show the user what was discovered and ask them to confirm or correct.

If no Linear:

> Got it — I'll skip the Linear integration. You can always set it up later by
> providing a Linear API key.

Mark all Linear fields in `environment.md` as `N/A - Linear not configured`.

---

## Step 3: Clone & Analyze Repos (AUTOMATIC)

**Goal:** Deep-dive into the codebase to understand architecture, tech stack, API
surface, frontend routing, test infrastructure, and deployment setup.

```bash
# Clone repos
mkdir -p ~/repos
cd ~/repos
for repo in <repo-list>; do
  gh repo clone "$repo" -- --depth=50
done
```

**Update `environment.md`:**

- `PLATFORM_REPO_PATH` — where the repo was cloned
- `AGENT_REPO_PATH` — if second repo exists

### 3a. Analyze Repository Structure

For each repo, systematically explore:

```bash
# Top-level structure
ls -la
cat README.md 2>/dev/null | head -100

# Package manager & dependencies
cat package.json 2>/dev/null | head -50        # Node
cat requirements.txt 2>/dev/null               # Python
cat Cargo.toml 2>/dev/null | head -30          # Rust
cat go.mod 2>/dev/null                         # Go
cat Gemfile 2>/dev/null | head -30             # Ruby

# Framework detection
find . -name "*.ts" -path "*/src/*" | head -20
find . -name "*.py" -path "*/app/*" | head -20

# Docker / deployment
find . -name "Dockerfile*" -o -name "docker-compose*" | head -10
find . -name "*.yml" -o -name "*.yaml" | grep -iE "ci|deploy|github|workflow" | head -10

# Environment / config
find . -name ".env*" -o -name "*.env*" | head -10
find . -name "config*" -path "*/src/*" | head -10

# API routes / endpoints
find . -name "routes*" -o -name "router*" -o -name "urls.py" | head -10
grep -r "app\.\(get\|post\|put\|delete\|patch\)" --include="*.ts" --include="*.js" -l | head -10
grep -r "@app\.route\|@router\." --include="*.py" -l | head -10

# Frontend routing
grep -r "Route\|path:" --include="*.tsx" --include="*.jsx" --include="*.vue" -l | head -10

# Database models / schemas
find . -name "*.model.*" -o -name "*.schema.*" -o -name "models.py" | head -10
find . -name "migration*" -type d | head -5

# Test infrastructure
find . -name "*.test.*" -o -name "*.spec.*" -o -name "test_*" | head -10
find . -name "jest*" -o -name "pytest*" -o -name "vitest*" | head -5

# CI/CD
ls -la .github/workflows/ 2>/dev/null
cat .github/workflows/*.yml 2>/dev/null | head -100
```

### 3b. Build Architecture Map

From the analysis, build a mental model:

1. **Tech stack** — language, framework, database, cache, message queue
2. **Service architecture** — monolith, microservices, monorepo? Which services?
3. **API surface** — REST, GraphQL, RPC? List main endpoint groups
4. **Frontend** — SPA, SSR, static? Framework? Routing structure?
5. **Authentication** — how do users log in? OAuth, email/password, magic links?
6. **Database** — MongoDB, Postgres, MySQL? ORM? Migration strategy?
7. **Deployment** — Docker, K8s, serverless? CI/CD pipeline?
8. **Test infrastructure** — existing tests? Unit? Integration? E2E?
9. **Environment config** — how are environments configured? `.env` files? Secrets manager?

### 3c. Identify QA-Critical Paths

From the architecture map, identify:

- **User-facing flows** — signup, login, core features, billing, settings
- **API endpoints** — which ones are public, which need auth?
- **Integration points** — third-party services, webhooks, OAuth providers
- **Data flows** — where does data get created, modified, deleted?
- **Error boundaries** — what happens when things fail?

### 3d. Report Findings to User

Share what you learned:

> Here's what I found in your codebase:
>
> **Stack:** [Node/TypeScript, React, MongoDB, Redis, etc.]
> **Architecture:** [Monorepo with API, Frontend, Worker services]
> **Key APIs:** [Auth, Users, Projects, Billing — X endpoints total]
> **Frontend:** [React SPA, Y routes under /dashboard]
> **Database:** [MongoDB with Z collections]
> **Deployment:** [Docker, deployed to AWS/GCP/etc.]
> **Existing tests:** [Jest unit tests covering A%, no E2E]
>
> Does this look right? Anything I'm missing?

---

## Step 4: Build Knowledge Base (AUTOMATIC)

**Goal:** Create the knowledge base directory that the QA skills reference.

```bash
KB_PATH="{PLATFORM_REPO_PATH}/knowledgebase"
mkdir -p "$KB_PATH"/{platform,bugs,test-strategies,checklists}
```

### 4a. Generate Platform Docs

From the repo analysis, auto-generate initial knowledge base files:

For each major feature area discovered in Step 3:

```bash
# Create platform doc
cat > "$KB_PATH/platform/<area>.md" << 'EOF'
# <Area Name>

## Overview
<What this feature does, based on code analysis>

## Routes / Endpoints
<API endpoints and frontend routes>

## Data Model
<Collections/tables involved, key fields>

## Authentication
<What auth is required>

## Edge Cases & Gotchas
<To be filled as QA discovers issues>

## Known Issues
<To be filled>
EOF
```

Generate:

- `README.md` — index of all platform docs
- `bugs/patterns.md` — empty template for recurring patterns
- `bugs/known-issues.md` — empty template for active bugs
- One `platform/<area>.md` per major feature area
- `test-strategies/` — common test strategy templates

**Update `environment.md`:**

- `KNOWLEDGEBASE_PATH` — path to the knowledge base directory

### 4b. Present Knowledge Base to User

> I've created an initial knowledge base from your codebase with docs for:
> [list areas]. I'll keep updating this as I test — it gets smarter over time.

---

## Step 5: Infrastructure Discovery (CONVERSATIONAL)

**Goal:** Understand the deployment infrastructure and get access credentials.

This is the most conversational step — the questions depend entirely on what was
discovered in the repo analysis.

### 5a. Determine What's Needed

Based on the repo analysis:

**If Docker/Containerized deployment detected:**

> I see you're using Docker. For the QA environment, I need to know:
>
> - Where are containers deployed? (AWS EC2, ECS, K8s, etc.)
> - How do I access those machines? (SSH key, bastion host, kubectl?)
> - Where are Docker images stored? (ECR, Docker Hub, GHCR?)

**If cloud deployment detected (AWS/GCP/Azure):**

> I see [AWS/GCP/Azure] configuration. Do I have access to a dedicated QA/staging
> environment? I'll need:
>
> - Cloud credentials or CLI profile
> - IP addresses or hostnames for each service
> - SSH access to instances (if applicable)

**If serverless or PaaS:**

> I see you're deploying to [Vercel/Railway/Fly.io/etc.]. How do I access the
> staging environment? Do I have admin access or just the deployed URL?

**If no deployment config found:**

> I couldn't determine your deployment setup from the repo. Can you tell me:
>
> - Where is the staging/QA environment hosted?
> - How do I deploy new branches for testing?
> - What access do I need?

### 5b. Collect Infrastructure Details

Based on answers, progressively ask for and fill in:

**Always needed:**

- `APP_URL` — "What's the QA/staging frontend URL?"
- `API_URL` — "What's the QA/staging API URL?"

**If cloud-hosted:**

- Ask for `AWS_PROFILE` / credentials, `AWS_REGION`, `AWS_ACCOUNT_ID`
- Ask for server IPs/hostnames
- Ask for SSH key (can they provide it, or is it already on the machine?)
- Ask for container names

**If database access needed:**

- "How do I connect to the QA database?" → `MONGODB_CREDENTIAL_SERVICE` or connection string
- "Is there a Redis/cache layer?" → `REDIS_ENDPOINT`

**If S3/object storage used:**

- "Where should I upload QA reports?" → S3 bucket or alternative
- Set up `S3_PUBLIC_BUCKET`, `S3_REPORTS_PREFIX`, `S3_REPORTS_URL_BASE`

For each piece of information received, immediately update `environment.md`.

### 5c. Ask About Sensitive Credentials

For credentials that shouldn't be in plaintext:

```
ask_for_credentials(
  service: "<service-name>",
  fields: ["<credential-field>"],
  message: "I need <description> to <purpose>"
)
```

Then save via `save_credential()`. Reference them in `environment.md` as
`get_credential(service="<name>")` — never store the actual values in the file.

---

## Step 6: Test Account Setup (CONVERSATIONAL)

**Goal:** Ensure a test account exists and the agent can log in.

> I need a dedicated test account for the QA environment. Do you already have one,
> or should I create one?

**If they have one:**

- Get the email and password
- Save password: `save_credential(service="qa-test-account", type="api_key", key=<password>)`
- Update `environment.md`: `TEST_ACCOUNT_EMAIL`, `TEST_ACCOUNT_PASSWORD` (as credential reference)

**If they want you to create one:**

- Check if the codebase has a seed script or admin panel
- If DB access exists, create directly:
  ```bash
  # Adapt based on what was learned in Step 3 about auth/user models
  ```
- If no DB access, ask them to create one and give you credentials

**Verify login works:**

```bash
# Try to authenticate via the API (adapt based on discovered auth method)
curl -sf -X POST {API_URL}/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"{TEST_ACCOUNT_EMAIL}","password":"{TEST_ACCOUNT_PASSWORD}"}'
```

Or use the browser tool to log in visually and confirm it works.

---

## Step 7: Integrations & Team (CONVERSATIONAL)

**Goal:** Set up Slack notifications, team member references, and any other integrations.

### 7a. Slack (if available)

> Do you want QA reports and notifications in Slack? If so, which channel should I use?

If yes:

- Get the channel ID → `SLACK_PRIMARY_CHANNEL_ID`
- Ask who the tech lead is for sign-offs → `TECH_LEAD_NAME`, `TECH_LEAD_SLACK_ID`
- Ask who the team lead is → `TEAM_LEAD_NAME`, `TEAM_LEAD_SLACK_ID`
- Ask if there's a developer agent → `SLACK_DEVELOPER_AGENT_ID`

### 7b. Team Members

> Who should I report to? I need to know:
>
> - Who gives the final sign-off on QA reports? (Tech Lead)
> - Who should I escalate blockers to? (Team Lead)
> - Is there a developer agent I'll be collaborating with?

Fill in the Team Members section of `environment.md`.

### 7c. AI Provider Credentials (if applicable)

If the platform uses AI services and QA needs to test them:

> I see your app uses [Anthropic/OpenAI/etc.]. Do I need API keys to test
> AI-related features in the QA environment?

If yes, collect via `ask_for_credentials` and `save_credential`.

---

## Step 8: Validation (AUTOMATIC)

**Goal:** Verify everything works end-to-end.

### 8a. Validate Environment Config

Read `environment.md` and check every field is filled:

```python
# Pseudo-check
required_fields = [
    "APP_URL", "API_URL", "TEST_ACCOUNT_EMAIL", "TEST_ACCOUNT_PASSWORD",
    "GITHUB_ORG", "PLATFORM_REPO", "PLATFORM_REPO_PATH",
    "KNOWLEDGEBASE_PATH", "WORKSPACE_DIR", "TEST_RUNS_DIR"
]
# S3 and infra fields are optional depending on setup
```

### 8b. Run Connectivity Checks

```bash
# API reachable?
curl -sf {API_URL}/health && echo "✅ API healthy" || echo "❌ API unreachable"

# Frontend reachable?
curl -sf -o /dev/null -w "%{http_code}" {APP_URL} && echo "✅ Frontend up" || echo "❌ Frontend down"

# GitHub access?
gh repo view {GITHUB_ORG}/{PLATFORM_REPO} --json name && echo "✅ GitHub access" || echo "❌ GitHub access failed"

# Login works?
# (adapt based on discovered auth method)

# Linear access? (if configured)
# SSH access? (if configured)
# S3 access? (if configured)
```

### 8c. Run a Smoke Test

Use the `browser` tool to:

1. Navigate to `{APP_URL}`
2. Log in with the test account
3. Take a screenshot
4. Verify the dashboard loads

This proves the full pipeline works: browser → frontend → API → auth → dashboard.

### 8d. Final Summary

Present the complete setup to the user:

> ✅ _QA Agent Setup Complete_
>
> _Repos:_ {GITHUB*ORG}/{PLATFORM_REPO} [+ {AGENT_REPO}]
> \_Stack:* [tech stack summary]
> _QA Environment:_ {APP*URL}
> \_Test Account:* {TEST*ACCOUNT_EMAIL}
> \_Linear:* Connected / Not configured
> _Slack:_ #{channel-name} / Not configured
> _Knowledge Base:_ {X} platform docs generated
>
> _What I can do now:_
>
> - "Test PR #123" — deploy and test a specific PR
> - "Test staging" — test whatever's currently deployed
> - "Full QA" — comprehensive test of all areas
> - "Create a test plan for [feature]" — pre-implementation planning
>
> Anything you want me to test first?

---

## Adapting to Project Type

Not every project is a full-stack web app with Docker and AWS. Adapt:

**Simple frontend (no backend):**

- Skip all infra/DB/SSH sections
- Focus on: GitHub, app URL, browser testing, visual regression
- Simplify `environment.md` — only need APP_URL, test account (if auth exists)

**API-only (no frontend):**

- Skip browser testing sections
- Focus on: API endpoints, auth, payload validation, error codes
- Test with curl/HTTP client instead of browser

**Monolith (single server):**

- One IP, one container, simpler deploy
- Adapt deploy scripts accordingly

**Kubernetes:**

- Use `kubectl` instead of SSH
- Container names → pod/deployment names
- Different health check approach

**Serverless / PaaS:**

- No SSH access — use platform CLI/dashboard
- Deploy via `git push` or CI/CD trigger
- Focus on API + browser testing only

---

## Error Handling During Setup

**GitHub token doesn't work:**

> That token doesn't seem to have access to the repo. Can you check it has
> `repo` scope? You might need to authorize the org at
> https://github.com/settings/tokens

**Can't reach QA environment:**

> I can't reach {URL}. Is the environment running? Could be a firewall issue
> if I'm on a different network. Can you check?

**Login fails:**

> The test account login failed. Here's what I got: [error].
> Can you check the credentials or create a fresh test account?

**Missing infrastructure info:**

> I can still do browser-based QA testing without [SSH/DB/etc.] access — I just
> won't be able to debug failures as deeply. Want to proceed without it, or
> set it up later?

Always offer to continue with reduced capabilities rather than blocking entirely.

---

## Files Modified During Setup

| File                                        | What's Written                                            |
| ------------------------------------------- | --------------------------------------------------------- |
| `environment.md`                            | All environment-specific configuration values             |
| `{KNOWLEDGEBASE_PATH}/README.md`            | Knowledge base index                                      |
| `{KNOWLEDGEBASE_PATH}/platform/*.md`        | Platform feature docs (auto-generated from repo analysis) |
| `{KNOWLEDGEBASE_PATH}/bugs/patterns.md`     | Bug pattern template                                      |
| `{KNOWLEDGEBASE_PATH}/bugs/known-issues.md` | Known issues template                                     |

## Credentials Saved During Setup

| Service                      | Type    | When                              |
| ---------------------------- | ------- | --------------------------------- |
| `github`                     | token   | Step 1 (always)                   |
| `linear`                     | api_key | Step 2 (if Linear configured)     |
| `mongodb-qa`                 | api_key | Step 5 (if DB access provided)    |
| `qa-test-account`            | api_key | Step 6 (test account password)    |
| `anthropic-qa` / `openai-qa` | api_key | Step 7 (if AI credentials needed) |
