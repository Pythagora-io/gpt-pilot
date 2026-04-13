---
name: build-developer-agent
description: "Set up a complete developer agent from scratch — connect GitHub/Linear, set up repos, configure coding agents (Codex/Claude Code), optionally add Figma and AWS/S3, connect DNS, and verify everything works. Use when onboarding a new developer agent, bootstrapping a dev environment for a new project, or when someone says 'set up the developer agent', 'build the dev agent', 'onboard a new project'."
---

# Build Developer Agent

Step-by-step setup for a fully working developer agent. Each step must pass verification before moving to the next.

## 📸 MANDATORY: Screenshot Evidence

Every time the agent verifies something visual is working (web app running, app accessible via URL, browser loads), it MUST:

1. Open it in the browser using `browser(action="open", url=...)`
2. Take a screenshot using `browser(action="screenshot")`
3. Send the screenshot to the user as proof

This applies to: Step 2 (repo running), Step 4 (coding agent output), and Step 8 (final verification). A verification without a screenshot is an incomplete verification. No exceptions.

## 🔓 MANDATORY: User Must Be Able to Access the App

For web apps, the agent MUST expose the app on a port that the user can reach from their browser. This is not optional — the user must be able to open the URL themselves and see/use the app. Steps:

1. Ensure the port is open and accessible (check firewall, use a reverse proxy if needed)
2. Provide the user with the exact URL to open
3. If the app has login, provide working test credentials
4. The user confirming they can log in and use the app is the final gate before setup is complete

## Overview

1. Connect GitHub (required) + Linear (optional)
2. Set up repositories and verify they build/run
3. Create test user and verify login (if applicable)
4. Configure coding agents — Codex and/or Claude Code (at least one required)
5. Connect Figma (optional)
6. Connect AWS / S3 for report uploads (optional)
7. Connect custom DNS (optional)
8. Expose and verify the running environment

## Checklist

Create `setup-checklist.md` in the project directory at the start:

```markdown
# Developer Agent Setup Checklist

## Step 1: Connect GitHub & Linear

- [ ] User provided GitHub API key
- [ ] Verified GitHub access — listed target repos successfully
- [ ] User provided Linear API key (optional)
- [ ] Verified Linear access — listed teams/tickets (optional)
- [ ] Saved credentials via save_credential

## Step 2: Set Up Repositories

- [ ] Cloned target repo(s)
- [ ] Installed dependencies
- [ ] Built project successfully (no errors)
- [ ] Ran project (if web app: confirmed it starts and listens)
- [ ] Asked user for any missing environment variables
- [ ] 📸 Took screenshot of running app as evidence (if web app)
- [ ] Verified dev environment is functional

## Step 3: Create Test User & Verify Login (if applicable)

- [ ] Created test user account
- [ ] Verified login works
- [ ] Confirmed app is functional after login

## Step 4: Configure Coding Agents

- [ ] User provided Anthropic API key for Claude Code (optional)
- [ ] Verified Claude Code can launch and respond
- [ ] 📸 Took screenshot / saved output of Claude Code test as evidence
- [ ] User provided OpenAI API key for Codex (optional)
- [ ] Verified Codex can launch and respond
- [ ] 📸 Took screenshot / saved output of Codex test as evidence
- [ ] At least one coding agent confirmed working

## Step 5: Connect Figma (Optional)

- [ ] User provided Figma API key
- [ ] Verified Figma access — listed files or fetched a test file

## Step 6: Connect AWS / S3 (Optional)

- [ ] User provided AWS credentials (access key + secret)
- [ ] User provided S3 bucket name
- [ ] Verified S3 access — uploaded a test file
- [ ] Saved S3_BUCKET and S3_PUBLIC_URL for use by other skills

## Step 7: Connect Custom DNS (Optional)

- [ ] User provided domain name
- [ ] Configured DNS records (A/CNAME pointing to instance)
- [ ] Set up SSL certificate (Let's Encrypt or provided)
- [ ] Configured reverse proxy (nginx/caddy)
- [ ] Verified app accessible via domain

## Step 8: Expose & Verify (MANDATORY for web apps)

- [ ] Port opened and accessible from user's browser
- [ ] Provided user with URL and test credentials
- [ ] 📸 Took screenshot of exposed app as evidence
- [ ] User confirmed they can open the URL in their browser
- [ ] User confirmed they can log in with test credentials
- [ ] Full environment verified end-to-end
```

## Steps

### Step 1: Connect GitHub & Linear

#### GitHub (Required)

1. Ask the user for their GitHub personal access token (or use `ask_for_credentials`):
   ```
   ask_for_credentials(service="GitHub", fields=["api_key"],
     message="Provide a GitHub personal access token with repo access. Generate one at https://github.com/settings/tokens")
   ```
2. Save it: `save_credential(service="github", type="api_key", key=<token>)`
3. **Verify** — list the repos the user wants to work with:
   ```bash
   gh auth login --with-token <<< "$GITHUB_TOKEN"
   gh repo list <owner> --limit 10
   ```
   Or fetch the specific repos:
   ```bash
   gh repo view <owner>/<repo>
   ```
4. If verification fails, report the error and ask the user to check their token's permissions. Do not proceed until GitHub access is confirmed.

#### Linear (Optional)

1. Ask: "Do you want to connect Linear for ticket management? (optional)"
2. If yes, ask for the Linear API key:
   ```
   ask_for_credentials(service="Linear", fields=["api_key"],
     message="Provide your Linear API key. Generate one at https://linear.app/settings/api")
   ```
3. Save it: `save_credential(service="linear", type="api_key", key=<token>)`
4. **Verify** — fetch the viewer and teams:
   ```bash
   curl -s -H "Authorization: $LINEAR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"query":"{ viewer { id name } teams { nodes { id name } } }"}' \
     https://api.linear.app/graphql
   ```
5. If verification fails, report the error. Since Linear is optional, ask if they want to skip or fix.

✅ _Gate: GitHub must be verified. Linear is optional. Update checklist before proceeding._

### Step 2: Set Up Repositories

1. Ask the user which repositories to set up (they may have already mentioned them).
2. Clone each repo:
   ```bash
   gh repo clone <owner>/<repo> ~/projects/<repo>
   ```
3. For each repo, detect the project type and install dependencies:
   - Node.js: `npm install` (or `yarn` / `pnpm` based on lockfile)
   - Python: `pip install -r requirements.txt` or `poetry install`
   - Other: follow the repo's README or setup instructions
4. **Build** the project:
   - Node.js: `npm run build` (if a build step exists)
   - Check for errors. If the build fails, troubleshoot and fix before continuing.
5. **Run** the project:
   - If it's a web app: start the dev server, confirm it's listening on a port
   - If it's a CLI/library: run the test suite or a smoke test
   - If it's a web app, attempt to verify by hitting the local URL:
     ```bash
     curl -s -o /dev/null -w "%{http_code}" http://localhost:<port>/
     ```
   - **If the project fails to start due to missing environment variables:**
     a. Check the error output and the project's `.env.example` / docs for required vars
     b. Ask the user for each missing value:
     ```
     "The project needs these environment variables to run:
     - DATABASE_URL — your database connection string
     - STRIPE_SECRET_KEY — Stripe API key (if using payments)
     - ...
     Can you provide these?"
     ```
     c. Save them via `save_credential` where appropriate
     d. Write them to the project's `.env` file
     e. Retry starting the project
   - Keep asking for missing vars iteratively until the project starts successfully
6. **📸 MANDATORY SCREENSHOT (web apps):** Once the app is running, open it in the browser and take a screenshot:
   ```
   browser(action="open", url="http://localhost:<port>")
   browser(action="screenshot")
   ```
   Send the screenshot to the user as evidence that the app is running. This is _not optional_ — every web app must have visual proof it works before proceeding.
7. Do NOT proceed until the repo builds and runs successfully.

✅ _Gate: All repos build and run. Update checklist before proceeding._

### Step 3: Create Test User & Verify Login

> Skip this step if the application doesn't have user authentication.

Most web apps need a test user to verify the full flow works.

1. Check if the app has authentication (look for login pages, auth middleware, user models).
2. If it does, create a test user:
   - Check if there's a seed script, admin CLI, or registration endpoint
   - If the app has a registration flow, use it to create a test account
   - If there's a database, create the user directly via DB commands or a seed script
   - Suggested test credentials: `test@<project>.dev` / `TestUser2026!`
3. **Verify login** — attempt to authenticate:
   - For web apps: hit the login endpoint or navigate to the login page
   - Confirm the session/token is returned and subsequent authenticated requests work
4. Save the test credentials somewhere accessible (e.g. in the project setup notes).
5. If login doesn't work, debug and fix before proceeding.

✅ _Gate: Test user can log in (or auth is not applicable). Update checklist before proceeding._

### Step 4: Configure Coding Agents

At least one of Codex or Claude Code must be configured. Ask the user which they want (or both).

#### Claude Code (requires Anthropic API key)

1. Ask for the key:
   ```
   ask_for_credentials(service="Anthropic", fields=["api_key"],
     message="Provide your Anthropic API key for Claude Code. Get one at https://console.anthropic.com/settings/keys")
   ```
2. Save it: `save_credential(service="anthropic", type="api_key", key=<token>)`
3. **Verify** — launch a quick test:
   ```bash
   cd ~/projects/<repo> && \
   ANTHROPIC_API_KEY="$KEY" claude -p --print "Say hello and confirm you can see this repo. List the top-level files." 2>&1 | head -20
   ```
4. If it works, Claude Code is ready. **Save the output as evidence.**
   If it fails (auth error, not installed), troubleshoot:
   - Not installed: `npm install -g @anthropic-ai/claude-code`
   - Auth error: ask user to verify the key

#### Codex (requires OpenAI API key)

1. Ask for the key:
   ```
   ask_for_credentials(service="OpenAI", fields=["api_key"],
     message="Provide your OpenAI API key for Codex. Get one at https://platform.openai.com/api-keys")
   ```
2. Save it: `save_credential(service="openai", type="api_key", key=<token>)`
3. **Verify** — launch a quick test:
   ```bash
   cd ~/projects/<repo> && \
   OPENAI_API_KEY="$KEY" codex exec "Say hello and confirm you can see this repo. List the top-level files." 2>&1 | head -20
   ```
4. If it works, Codex is ready. **Save the output as evidence.**
   If it fails, troubleshoot:
   - Not installed: `npm install -g @openai/codex`
   - Auth error: ask user to verify the key

**Send the user the test output from each coding agent** so they can see it works.

✅ _Gate: At least one coding agent verified. Update checklist before proceeding._

### Step 5: Connect Figma (Optional)

1. Ask: "Do you want to connect Figma for design reference? (optional)"
2. If yes, ask for the key:
   ```
   ask_for_credentials(service="Figma", fields=["api_key"],
     message="Provide your Figma personal access token. Generate one at https://www.figma.com/developers/api#access-tokens")
   ```
3. Save it: `save_credential(service="figma", type="api_key", key=<token>)`
4. **Verify** — fetch the user's info:
   ```bash
   curl -s -H "X-Figma-Token: $FIGMA_KEY" https://api.figma.com/v1/me
   ```
5. If verification passes, Figma is connected. If not, report and offer to skip.

✅ _Gate: Figma verified or skipped. Update checklist._

### Step 6: Connect AWS / S3 (Optional)

Cross-review reports and plan files can be uploaded to S3 for easy sharing. This step is optional — if skipped, reports will only be available locally.

1. Ask: "Do you want to set up AWS/S3 for uploading cross-review reports? (optional)"
2. If yes, ask for credentials:
   ```
   ask_for_credentials(service="AWS", fields=["access_key_id", "secret_access_key"],
     message="Provide your AWS credentials for S3 access. The IAM user needs s3:PutObject and s3:GetObject on your bucket.")
   ```
3. Save them: `save_credential(service="aws", type="api_key", key=<access_key_id>, metadata={"secret": "<secret_key>"})`
4. Ask for the S3 bucket name and region:
   - "What S3 bucket should I use for report uploads? (e.g. `my-project-reports`)"
   - "What AWS region? (e.g. `us-east-1`)"
5. Configure AWS CLI:
   ```bash
   aws configure set aws_access_key_id "$ACCESS_KEY"
   aws configure set aws_secret_access_key "$SECRET_KEY"
   aws configure set region "$REGION"
   ```
6. **Verify** — upload a test file:
   ```bash
   echo "test" | aws s3 cp - "s3://$BUCKET/test-upload.txt"
   aws s3 rm "s3://$BUCKET/test-upload.txt"
   ```
7. Store the bucket config for other skills to use:
   - `S3_BUCKET` — the bucket name
   - `S3_PUBLIC_URL` — the public URL prefix (e.g. `https://$BUCKET.s3.$REGION.amazonaws.com`)
   - Save these in the project config or environment

✅ _Gate: S3 verified or skipped. Update checklist._

### Step 7: Connect Custom DNS (Optional)

If the user wants to serve the app on a real domain instead of an IP:port.

1. Ask: "Do you want to set up a custom domain for this app? (optional)"
2. If yes, ask for the domain: "What domain should point to this app? (e.g. `dev.myproject.com`)"
3. Guide the user to update their DNS:
   - "Please add an A record pointing `<domain>` to `<server-ip>`, or a CNAME to your instance hostname."
   - "Let me know once the DNS record is set."
4. Wait for DNS propagation and verify:
   ```bash
   dig +short <domain>
   ```
5. Set up SSL with Let's Encrypt:
   ```bash
   sudo certbot certonly --nginx -d <domain>
   ```
   Or if the user provides their own certificate, use that.
6. Configure nginx (or caddy) as a reverse proxy:
   ```nginx
   server {
       listen 443 ssl;
       server_name <domain>;
       ssl_certificate /etc/letsencrypt/live/<domain>/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/<domain>/privkey.pem;
       location / {
           proxy_pass http://127.0.0.1:<app-port>;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```
7. Reload nginx and verify:
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   curl -s -o /dev/null -w "%{http_code}" https://<domain>/
   ```
8. If it loads, DNS setup is complete.

✅ _Gate: Domain verified or skipped. Update checklist._

### Step 8: Expose & Verify

For web apps:

1. Ensure the dev server is running from Step 2.
2. Determine the port it's running on.
3. If a custom domain was set up (Step 7), provide that URL.
4. Otherwise, if the instance is remote (VPS/cloud), expose the port:
   - Check if a reverse proxy (nginx, caddy) is available
   - Or use a simple port forward / tunnel
   - Or just confirm the port is accessible (firewall rules)
5. Provide the user with the URL to access the app.
6. **📸 MANDATORY SCREENSHOT:** Open the URL in the browser and take a screenshot:
   ```
   browser(action="open", url="<URL>")
   browser(action="screenshot")
   ```
   Send the screenshot to the user as evidence the app is accessible.
7. Send the user:
   - The URL to open in their browser
   - Test credentials (from Step 3) if the app has login
   - "Please open this URL and confirm you can log in."
8. **Wait for the user to confirm** they can open the URL AND log in. This is the final gate. Do not mark setup as complete until the user says it works from their browser.

For non-web projects:

1. Confirm the test suite passes or the CLI runs correctly.
2. Show the user the output as verification.

✅ _Gate: User confirms they can access and log in to the app. Update checklist — setup complete._

## Completion

When all required steps pass:

```
✅ Developer agent setup complete!

Summary:
- GitHub: Connected ✓
- Linear: {Connected ✓ / Skipped}
- Repos: {list of repos} — built and running ✓
- Test user: {Created ✓ / Not applicable}
- Coding agents: {Claude Code ✓ / Codex ✓ / Both ✓}
- Figma: {Connected ✓ / Skipped}
- AWS/S3: {Connected ($BUCKET) ✓ / Skipped}
- DNS: {Connected ($DOMAIN) ✓ / Skipped}
- Environment: Verified and accessible ✓
```
