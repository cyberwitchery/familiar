# infra profile

## change discipline
- plan first: what changes, impact, rollback.
- no production changes without explicit instruction.
- keep diffs minimal; avoid churn in generated files.

## safety
- least privilege everywhere (iam/rbac/security groups).
- avoid opening 0.0.0.0/0 unless explicitly required and documented.
- pin versions (providers, modules, images) when practical.

## verification
- include exact commands (e.g. terraform fmt/validate/plan, kubectl diff, helm template).
- highlight drift risks and rollout steps.
