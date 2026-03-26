---
name: infrastructure-audit
description: Audit cloud infrastructure for security vulnerabilities, cost optimization opportunities, and best-practice compliance. Use when the user wants a health check of their AWS/GCP/Azure setup, needs to review IAM policies, or wants to find cost savings.
---

# Infrastructure Audit

Perform a systematic review of the user's cloud infrastructure.

## Audit Checklist

### Security
1. Review IAM policies and roles — look for overly permissive policies (`*` actions, `*` resources)
2. Check for public S3 buckets / storage objects
3. Verify encryption at rest and in transit
4. Review security group / firewall rules for open ports
5. Check for unused credentials and access keys older than 90 days
6. Verify MFA is enabled for root and admin accounts

### Cost
1. Identify unused resources (unattached EBS volumes, idle instances, orphaned snapshots)
2. Review instance sizing — suggest rightsizing based on utilization
3. Check for Reserved Instance / Savings Plan coverage
4. Identify resources without cost allocation tags
5. Review data transfer costs and suggest optimizations

### Reliability
1. Check for single points of failure (single-AZ deployments)
2. Verify backup and disaster recovery configurations
3. Review auto-scaling policies
4. Check health check configurations for load balancers
5. Verify logging and monitoring coverage

## Output Format

Present findings as a prioritized list with:
- **Critical**: Immediate security risks or production reliability issues
- **High**: Should be addressed within a week
- **Medium**: Best-practice improvements
- **Low**: Nice-to-have optimizations

For each finding, provide:
1. What was found
2. Why it matters
3. How to fix it (with commands or IaC snippets)
