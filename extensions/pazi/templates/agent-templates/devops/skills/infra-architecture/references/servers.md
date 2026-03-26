# Server Inventory

List of servers the agent has access to. Updated during onboarding.

## Servers

<!-- For each server:
| Hostname | IP | Role | Provider | SSH User | Process Manager | Key Services |
|---|---|---|---|---|---|---|
| web-1 | 1.2.3.4 | Web server | AWS | devops-readonly | systemd | nginx, node |
-->

| Hostname             | IP  | Role | Provider | SSH User | Process Manager | Key Services |
| -------------------- | --- | ---- | -------- | -------- | --------------- | ------------ |
| _not yet configured_ |     |      |          |          |                 |              |

## SSH Access

```bash
# Template — update with actual key path and user
ssh -i ~/.ssh/devops-agent devops-readonly@<ip>
```

## Common Commands Per Server

<!-- Fill in as you learn what runs where -->

```bash
# Check process status
# sudo systemctl status <service>
# sudo supervisorctl status
# sudo docker ps

# Read logs
# sudo journalctl -u <service> -n 50 --no-pager
# tail -50 /var/log/<app>.log
```
