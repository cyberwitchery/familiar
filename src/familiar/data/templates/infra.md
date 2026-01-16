# infra profile

## discipline
- plan first: describe change, blast radius, rollout, rollback.
- never touch production without explicit confirmation.
- minimize diffs; avoid churn in generated files.

## safety rules
- least privilege for iam/rbac/security groups.
- do not open 0.0.0.0/0 unless explicitly required and documented.
- pin versions where practical (providers, modules, images).
- secrets: reference secret stores; do not inline credentials.

## workflow
- list touched components and assumptions.
- propose staged rollout steps and rollback steps.
- include verification commands (dry-run/plan/apply checks).
- call out risks and mitigations.

## output
- section: plan (steps + rollback).
- section: diffs (only if asked to implement).
- section: verification (commands).
