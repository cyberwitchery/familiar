task: plan and execute an infrastructure change.

## inputs

- $ARGUMENTS (required): description of the change, target environment, and any constraints.

## preconditions

STOP and ask if:
- the target environment is not specified (dev/staging/prod)
- the region, account, or project is unclear
- you don't have enough context to assess blast radius
- this is a production change and you haven't received explicit approval

NEVER proceed with production changes without explicit approval in this conversation.

## required information

before planning, confirm you know:
1. **what**: what exactly is changing?
2. **why**: what problem does this solve?
3. **where**: which environment, region, account?
4. **when**: is there a maintenance window or timing constraint?
5. **who**: who needs to approve this?

## planning checklist

for every change, document:

**blast radius**
- what resources are directly affected?
- what depends on those resources?
- what's the worst case if this fails?

**rollout plan**
- can this be done incrementally?
- what's the order of operations?
- what gates/checkpoints exist?

**rollback plan**
- how do we undo this?
- how long would rollback take?
- is rollback even possible (destructive changes)?

**risks**
- what could go wrong?
- how do we detect failure?
- what's the mitigation for each risk?

## steps

1. **gather**: confirm all required information is available.
2. **assess**: document blast radius and risks.
3. **plan**: write rollout and rollback steps.
4. **review**: present plan for approval before any implementation.
5. **dry-run**: run plan/diff commands to preview changes.
6. **apply**: execute only after explicit approval.
7. **verify**: confirm the change worked as expected.

## output

```
## change summary
<1-2 sentence description>

## environment
<env> - <region/account/project>

## blast radius
- directly affected: <resources>
- dependencies: <what relies on these>
- worst case: <if this fails completely>

## rollout plan
1. <step with verification>
2. <step with verification>
3. <step with verification>

## rollback plan
1. <step>
2. <step>
estimated rollback time: <duration>

## risks and mitigations
| risk | likelihood | impact | mitigation |
|------|------------|--------|------------|
| <risk> | low/med/high | <impact> | <mitigation> |

## verification
<commands to confirm success>

## approval needed
- [ ] <approver> has approved this change
```
