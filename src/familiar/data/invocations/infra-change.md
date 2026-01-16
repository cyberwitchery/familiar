task: infrastructure change plan.

inputs
- $ARGUMENTS (required): desired change (what/why), target env (dev/prod), constraints.

preconditions
- if required info is missing (env, region, account, constraints): ask; stop.
- do not propose or apply production changes without explicit approval.

steps
- list touched components and assumptions.
- describe blast radius and failure modes.
- propose rollout steps (staged) and rollback steps.
- highlight least-privilege and exposure risks.
- include verification commands (plan/dry-run/diff/apply checks).

acceptance
- plan is actionable, ordered, and includes rollback.
- no broad permissions or public exposure without explicit justification.
- diffs are minimal (only if asked to implement).

output
- plan (rollout + rollback).
- diffs (only if asked).
- verification commands.
