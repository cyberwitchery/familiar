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

## frontend

react frontend guidelines:

**default commands:**

- lint: `npm run lint`
- typecheck: `npm run typecheck`
- test: `npm test`

**rules:**

- no `any` in TypeScript
- no console.log in production
- accessibility required (labels, keyboard nav, focus states)
- keep components under ~100 lines
- use React Testing Library, test behavior not implementation

## docs

documentation guidelines:

- know your audience before writing
- active voice, concrete examples, front-load important info
- structure: README (quick start), tutorials (teach by building), how-to (goal-oriented), reference (scannable)
- every code example must be correct, minimal, and self-contained

## data

data engineering guidelines:

**critical rules:**

- always use parameterized queries (never string concatenation)
- no unreviewed SQL against production
- no DELETE/UPDATE/TRUNCATE on production without explicit approval

**patterns:**

- transactional DBs: use transactions, verify before COMMIT
- analytical DBs: prefer immutable patterns (new partitions, not updates)
- pipelines: idempotent, atomic, validated

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
