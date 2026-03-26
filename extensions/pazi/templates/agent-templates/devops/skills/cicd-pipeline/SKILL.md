---
name: cicd-pipeline
description: Design, build, and troubleshoot CI/CD pipelines. Use when the user needs to set up GitHub Actions, GitLab CI, or other pipeline systems, or when debugging build/deploy failures.
---

# CI/CD Pipeline Management

Help users create, optimize, and debug continuous integration and deployment pipelines.

## When Creating a New Pipeline

1. Ask about the project's language/framework and deployment target
2. Understand the testing requirements (unit, integration, e2e)
3. Determine the deployment strategy (blue-green, canary, rolling)
4. Check for existing pipeline files before creating new ones

## Pipeline Best Practices

- **Fast feedback**: Put the fastest checks first (lint, type-check, then unit tests, then integration)
- **Caching**: Always cache dependencies (node_modules, pip cache, Go modules)
- **Parallelism**: Run independent jobs concurrently
- **Artifacts**: Upload test results and coverage reports as artifacts
- **Environment isolation**: Use matrix builds for multi-version testing
- **Secrets management**: Never hardcode secrets — use the CI platform's secret store
- **Fail fast**: Exit on first failure to save compute time

## When Debugging Pipeline Failures

1. Read the full error output before suggesting fixes
2. Check for common issues:
   - Dependency version conflicts
   - Missing environment variables
   - Docker layer caching issues
   - Network timeouts in CI environments
   - Permission errors (file system, API keys)
3. Suggest adding more verbose logging to narrow down the issue
4. Recommend running the failing step locally when possible

## Deployment Stages

Recommend a standard promotion path:
1. **Build** → Compile, lint, test
2. **Staging** → Deploy to staging, run smoke tests
3. **Production** → Deploy with strategy (canary/blue-green), verify health checks
4. **Post-deploy** → Run synthetic monitoring, notify team
