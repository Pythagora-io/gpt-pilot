# Environment Configuration

Fill in all values below before using the QA skills. These are referenced throughout
the skill files as `{PLACEHOLDER_NAME}` — the QA agent reads this file at the start
of every test run to resolve environment-specific values.

## Application URLs

| Variable                   | Description                           | Example                                       |
| -------------------------- | ------------------------------------- | --------------------------------------------- |
| `APP_URL`                  | Frontend URL (staging/QA environment) | `https://qa.example.com`                      |
| `API_URL`                  | API URL                               | `https://api.qa.example.com`                  |
| `APP_PRODUCTION_URL`       | Production frontend URL               | `https://example.com`                         |
| `WORKSPACE_CONTROLLER_URL` | Workspace controller URL              | `https://workspace-controller.qa.example.com` |

## Test Account

| Variable                | Description           | Example          |
| ----------------------- | --------------------- | ---------------- |
| `TEST_ACCOUNT_EMAIL`    | QA test user email    | `qa@example.com` |
| `TEST_ACCOUNT_PASSWORD` | QA test user password | `TestPass123!`   |

## AWS / Cloud Infrastructure

| Variable         | Description           | Example                                            |
| ---------------- | --------------------- | -------------------------------------------------- |
| `AWS_ACCOUNT_ID` | AWS account ID        | `123456789012`                                     |
| `AWS_REGION`     | AWS region            | `us-east-1`                                        |
| `AWS_PROFILE`    | AWS CLI profile name  | `qa-playground`                                    |
| `ECR_REGISTRY`   | ECR registry URL      | `123456789012.dkr.ecr.us-east-1.amazonaws.com`     |
| `ECR_PREFIX`     | ECR repository prefix | `qa/api`, `qa/frontend`, `qa/workspace-controller` |

## EC2 Instances

| Variable               | Description                      | Example                |
| ---------------------- | -------------------------------- | ---------------------- |
| `API_EC2_IP`           | API server IP                    | `10.0.1.100`           |
| `FRONTEND_EC2_IP`      | Frontend server IP               | `10.0.1.101`           |
| `WS_CONTROLLER_EC2_IP` | Workspace controller IP          | `10.0.1.102`           |
| `SSH_KEY_PATH`         | Path to SSH private key          | `~/.ssh/my-qa-key.pem` |
| `SSH_USER_EC2`         | SSH user for EC2 instances       | `ec2-user`             |
| `SSH_USER_WORKSPACE`   | SSH user for workspace instances | `ubuntu`               |

## S3 Buckets

| Variable                 | Description                              | Example                                                          |
| ------------------------ | ---------------------------------------- | ---------------------------------------------------------------- |
| `S3_PUBLIC_BUCKET`       | Public S3 bucket for reports/screenshots | `my-qa-public-assets`                                            |
| `S3_PRIVATE_BUCKET`      | Private S3 bucket                        | `my-qa-private-assets`                                           |
| `S3_USER_DATA_BUCKET`    | User data S3 bucket                      | `my-qa-user-data`                                                |
| `S3_REPORTS_PREFIX`      | Prefix path for QA reports in S3         | `reports/`                                                       |
| `S3_REPORTS_URL_BASE`    | Public URL base for reports              | `https://my-qa-public-assets.s3.us-east-1.amazonaws.com/reports` |
| `S3_AGENT_ASSETS_BUCKET` | Bucket for agent boot scripts            | `my-agent-assets`                                                |

## Database

| Variable                     | Description                         | Example                                              |
| ---------------------------- | ----------------------------------- | ---------------------------------------------------- |
| `MONGODB_CREDENTIAL_SERVICE` | Service name for `get_credential()` | `mongodb-qa`                                         |
| `MONGODB_DEFAULT_DB`         | Default MongoDB database name       | `qaDB`                                               |
| `REDIS_ENDPOINT`             | Redis/ElastiCache endpoint          | `my-redis.abc123.0001.use1.cache.amazonaws.com:6379` |

## AI Provider Credentials

| Variable                       | Description                         | Example        |
| ------------------------------ | ----------------------------------- | -------------- |
| `ANTHROPIC_CREDENTIAL_SERVICE` | Service name for `get_credential()` | `anthropic-qa` |
| `OPENAI_CREDENTIAL_SERVICE`    | Service name for `get_credential()` | `openai-qa`    |

## Docker Containers

| Variable                       | Description                         | Example                  |
| ------------------------------ | ----------------------------------- | ------------------------ |
| `API_CONTAINER_NAME`           | API Docker container name           | `my-api-production`      |
| `FRONTEND_CONTAINER_NAME`      | Frontend Docker container name      | `my-frontend-production` |
| `WS_CONTROLLER_CONTAINER_NAME` | WS Controller Docker container name | `my-wsc-production`      |

## GitHub / Source Code

| Variable             | Description                 | Example                  |
| -------------------- | --------------------------- | ------------------------ |
| `GITHUB_ORG`         | GitHub organization         | `my-org`                 |
| `PLATFORM_REPO`      | Main platform repo name     | `my-platform`            |
| `AGENT_REPO`         | Agent repo name             | `my-agent`               |
| `PLATFORM_REPO_PATH` | Local path to platform repo | `/home/user/my-platform` |
| `AGENT_REPO_PATH`    | Local path to agent repo    | `/home/user/my-agent`    |

## Linear (Project Management)

| Variable                   | Description                             | Example                                |
| -------------------------- | --------------------------------------- | -------------------------------------- |
| `LINEAR_CREDENTIAL_PATH`   | Path to Linear API key in auth-profiles | (auto-detected from OpenClaw config)   |
| `LINEAR_QA_USER_ID`        | Linear user ID for the QA agent         | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` |
| `LINEAR_QA_STATE_ID`       | Linear state ID for "QA" status         | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` |
| `LINEAR_TODO_STATE_ID`     | Linear state ID for "Todo" status       | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` |
| `LINEAR_BLOCKED_STATE_ID`  | Linear state ID for "Blocked" status    | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` |
| `LINEAR_DEVELOPER_USER_ID` | Linear user ID for the developer agent  | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` |

## Slack

| Variable                   | Description                                | Example       |
| -------------------------- | ------------------------------------------ | ------------- |
| `SLACK_PRIMARY_CHANNEL_ID` | Main Slack channel for QA notifications    | `C0XXXXXXXXX` |
| `SLACK_TECH_LEAD_ID`       | Slack user ID for Tech Lead                | `U0XXXXXXXXX` |
| `SLACK_TEAM_LEAD_ID`       | Slack user ID for Team Lead (if different) | `U0XXXXXXXXX` |
| `SLACK_DEVELOPER_AGENT_ID` | Slack user ID for developer agent          | `U0XXXXXXXXX` |

## Team Members

| Variable              | Description                            | Example                                |
| --------------------- | -------------------------------------- | -------------------------------------- |
| `TEAM_LEAD_NAME`      | Name of team/project lead              | `Jane`                                 |
| `TEAM_LEAD_LINEAR_ID` | Linear user ID for team lead           | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` |
| `TEAM_LEAD_SLACK_ID`  | Slack user ID for team lead            | `U0XXXXXXXXX`                          |
| `TECH_LEAD_NAME`      | Name of tech lead (sign-off authority) | `John`                                 |
| `TECH_LEAD_SLACK_ID`  | Slack user ID for tech lead            | `U0XXXXXXXXX`                          |

## Knowledge Base

| Variable             | Description                         | Example                                |
| -------------------- | ----------------------------------- | -------------------------------------- |
| `KNOWLEDGEBASE_PATH` | Path to QA knowledge base directory | `/home/user/my-platform/knowledgebase` |

## Workspace Directory

| Variable        | Description                      | Example                       |
| --------------- | -------------------------------- | ----------------------------- |
| `WORKSPACE_DIR` | OpenClaw workspace directory     | `~/.openclaw/workspace-my-qa` |
| `TEST_RUNS_DIR` | Directory for test run artifacts | `test-runs/`                  |
