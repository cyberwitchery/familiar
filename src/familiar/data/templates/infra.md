# infrastructure

this involves infrastructure changes. infrastructure mistakes can cause outages, data loss, or security breaches. proceed with extreme caution, especially for production environments.

## critical constraints

STOP and ask before:
- making ANY change to a production environment
- modifying IAM policies, security groups, or network ACLs
- changing database schemas or configurations
- modifying secrets, certificates, or encryption settings

NEVER:
- apply changes to production without explicit approval in this conversation
- use `0.0.0.0/0` for ingress without explicit justification
- inline secrets, tokens, or credentials—always reference secret stores
- grant `*` permissions or admin/root access as a shortcut
- skip the plan/dry-run step

## before any change

identify and state:
1. **environment**: which environment (dev/staging/prod)?
2. **blast radius**: what resources are affected? what depends on them?
3. **rollback**: how do we undo this if it fails?
4. **dependencies**: what must happen before/after this change?

## change process

1. **plan**: describe the change and its expected impact
2. **dry-run**: run `terraform plan`, `kubectl diff`, or equivalent
3. **review**: present the diff and wait for approval
4. **stage**: apply to non-production first when possible
5. **apply**: apply to production only after explicit approval
6. **verify**: confirm the change worked as expected

## safety checklist

before proposing any change, verify:
- [ ] least-privilege: permissions are minimal and scoped
- [ ] versions pinned: providers, modules, images have explicit versions
- [ ] secrets external: no credentials in code, referenced from vault/secrets manager
- [ ] idempotent: applying twice produces the same result
- [ ] reversible: rollback steps are documented and tested

## output format

```
## environment
<dev|staging|prod> - <region/account/project>

## change summary
<1-2 sentence description>

## blast radius
<what resources are affected, what depends on them>

## rollout steps
1. <step>
2. <step>

## rollback steps
1. <step>
2. <step>

## verification
<commands to confirm success>
```
