# Environment Variables & Configuration

Track where environment variables are managed and what each service needs.

## Environment Management

<!-- How env vars are deployed: .env files, SSM, Vault, k8s secrets, etc. -->

| Method    | Used by       | Location               |
| --------- | ------------- | ---------------------- |
| _example_ | _API service_ | _/app/.env or AWS SSM_ |

## Key Variables Per Service

<!-- List the important env vars for each service — NOT the values, just the names and what they do -->

### Service: _example_

| Variable       | Purpose                     |
| -------------- | --------------------------- |
| `DATABASE_URL` | Primary database connection |
| `REDIS_URL`    | Cache connection            |
| `API_KEY`      | External API authentication |

## Config Files

<!-- Non-env configuration: nginx configs, supervisor configs, etc. -->

| File                                | Server  | Purpose                |
| ----------------------------------- | ------- | ---------------------- |
| _/etc/nginx/sites-enabled/app.conf_ | _web-1_ | _Reverse proxy config_ |
