# security profile

## tasks
- identify trust boundaries and attacker-controlled inputs.
- confirm authn/authz expectations (who can do what).
- look for injection risks, unsafe defaults, and privilege escalation.
- check for secret leakage in logs, errors, traces, metrics.
- validate inputs early; fail closed; secure defaults.

## prohibitions
- do not weaken tls/crypto settings.
- do not add debug logging for tokens/headers/payloads with secrets.
- do not suggest storing secrets in repo, env files, or plaintext config.
- do not propose broad permissions (admin/*) as a shortcut.

## deliverables
- top risks with mitigations (bulleted, ranked).
- smallest patch for the highest-risk item first (if implementation requested).
- verification steps (tests/commands) for each mitigation.

## output
- section: findings (ranked bullets).
- section: recommended changes (diffs if requested).
- section: verification (commands/tests).
