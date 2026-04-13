# S3 Configuration

Upload settings for QA reports and screenshots.

## Credentials

Use the AWS CLI profile configured in `environment.md`, or set credentials via
environment variables:

```
AWS_PROFILE={AWS_PROFILE}
# OR
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key>
AWS_DEFAULT_REGION={AWS_REGION}
```

**Do NOT hardcode AWS credentials in skill files.** Use `get_credential()`, AWS CLI
profiles, or environment variables.

## Bucket & Paths

| Setting         | Value                                        |
| --------------- | -------------------------------------------- |
| Bucket          | `{S3_PUBLIC_BUCKET}`                         |
| Reports prefix  | `{S3_REPORTS_PREFIX}`                        |
| Report path     | `{S3_REPORTS_PREFIX}qa-{run-id}/report.html` |
| Public URL base | `{S3_REPORTS_URL_BASE}`                      |

## Upload Commands

### Screenshots

```bash
aws s3 sync "{testFolder}/screenshots/" \
  "s3://{S3_PUBLIC_BUCKET}/{S3_REPORTS_PREFIX}qa-{run-id}/screenshots/" \
  --content-type image/png --profile {AWS_PROFILE}
```

### HTML Report

```bash
aws s3 cp reports/qa-{run-id}.html \
  "s3://{S3_PUBLIC_BUCKET}/{S3_REPORTS_PREFIX}qa-{run-id}/report.html" \
  --content-type "text/html" --profile {AWS_PROFILE}
```
