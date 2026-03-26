# Deploy Checklist

Generic checklist — customize per service.

## Pre-Deploy

- [ ] Current version noted (for rollback)
- [ ] Health checks passing
- [ ] No active incidents
- [ ] Team notified
- [ ] Rollback plan ready

## During Deploy

- [ ] Deploy command executed
- [ ] Watching logs for errors
- [ ] Health endpoint responding

## Post-Deploy

- [ ] Health checks passing
- [ ] No new errors in monitoring
- [ ] Key user flows tested (manual or automated)
- [ ] Team notified of success

## If Something Goes Wrong

1. Don't panic
2. Check error logs immediately
3. If user-facing impact: rollback first, investigate second
4. If no user impact: investigate, then decide whether to rollback or hotfix
5. Document what happened in `infra-debugging` skill
