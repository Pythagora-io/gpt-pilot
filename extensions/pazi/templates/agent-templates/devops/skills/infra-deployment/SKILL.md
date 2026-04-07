---
name: infra-deployment
description: Deployment runbooks for all services. Use before deploying anything or when asked about deployment procedures. Each runbook has pre-flight checks, commands, verification, and rollback. Triggers on "deploy", "release", "push to production", "rollback", "publish", "ship", "how do I deploy", "deployment process".
---

# Deployment Runbook

Read the appropriate runbook before deploying. **This agent has READ-ONLY access — it cannot deploy, but it can guide the user through the process and verify results.**

## Service Map

<!-- Fill in as you learn about the user's deployment setup -->

| Service   | Deploy Method      | Propagation | Runbook                        |
| --------- | ------------------ | ----------- | ------------------------------ |
| _example_ | _git push → CI/CD_ | _~2 min_    | _references/deploy-example.md_ |

## Before ANY Deploy

1. Verify current health (check monitoring)
2. Know the current version (for rollback)
3. Check for active users who may be affected
4. Have rollback command ready

## Deployment Methods

<!-- Document which method each service uses -->

### CI/CD Pipeline

_Not yet configured — document the user's CI/CD setup here._

### Manual Deploy

_Not yet configured — document SSH deploy steps here._

### Container-Based

_Not yet configured — document container registry, image tags, etc._

## Rollback Procedures

<!-- For each service: how to roll back to the previous version -->

| Service   | Rollback method                                         |
| --------- | ------------------------------------------------------- |
| _example_ | _Revert commit and re-deploy / Roll back container tag_ |

## Reference Files

- `references/deploy-checklist.md` — Generic pre/post deploy checklist
