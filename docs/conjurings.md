# conjurings

conjurings are system-level instructions that shape how the agent approaches tasks. they're combined when you run `conjure`.

## core

always included. defines fundamental behavior:

- smallest correct change, no drive-by refactors
- restate task, list files, implement in small steps
- run format + lint + tests
- ask before adding dependencies or changing public apis
- never print secrets

## rust

rust-specific guidelines:

**default commands:**

- format: `cargo fmt`
- lint: `cargo clippy --all-targets --all-features -- -D warnings`
- test: `cargo test --all-features`
- build: `cargo build --all-features`

**rules:**

- no unsafe without explicit rationale
- avoid new crates unless strong reason
- keep errors structured
- add tests for parsing/edge cases

## python

python-specific guidelines:

**default commands:**

- format: `ruff format`
- lint: `ruff check`
- type: `mypy .`
- test: `pytest -q`

**rules:**

- keep functions small
- add tests for boundary cases
- avoid widening public apis
- prefer explicit types at module boundaries

## infra

infrastructure/devops guidelines:

- plan first: what changes, impact, rollback
- no production changes without explicit instruction
- least privilege everywhere (iam/rbac/security groups)
- avoid 0.0.0.0/0 unless explicitly required
- pin versions (providers, modules, images)
- include verification commands (terraform, kubectl, helm)

## sec

security-focused guidelines:

**always do:**

- identify trust boundaries + attacker-controlled inputs
- confirm authn/authz expectations
- check for secret leakage
- validate input early, fail closed, secure defaults

**never do:**

- weaken tls/crypto settings
- add debug logging of secrets
- introduce permissive wildcard policies

## combining conjurings

conjurings are additive. order doesn't matter.

```bash
# rust project with security focus
familiar conjure codex rust sec

# python infrastructure tooling
familiar conjure claude python infra

# all conjurings
familiar conjure codex rust python infra sec
```
