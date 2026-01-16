task: security review.

inputs
- $ARGUMENTS (optional): scope. if empty, infer from current diff/repo context.

preconditions
- if scope is unclear and no obvious target exists: ask what to review; stop.

steps
- identify trust boundaries and attacker-controlled inputs.
- confirm authn/authz expectations.
- check for:
  - injection (sql, shell, template, path)
  - unsafe deserialization / parsing
  - secrets handling
  - permissions / privilege escalation
  - insecure defaults
- produce a ranked list of issues.

deliverables
- findings ranked by severity (high/med/low) with concrete mitigations.
- for each high item: smallest patch suggestion.
- verification steps for each mitigation (tests/commands).

output
- findings (ranked bullets).
- recommended changes (diff only if requested).
- verification commands/tests.
