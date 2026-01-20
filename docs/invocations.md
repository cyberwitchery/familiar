# invocations

invocations are task-specific prompts with placeholder substitution.

## add-tests

add tests for specified code.

```bash
familiar invoke codex add-tests "the parse_config function"
```

covers happy path, edge case, and failure mode.

## code-review

review code for issues.

```bash
familiar invoke codex code-review "the new authentication module"
```

checks correctness, clarity, maintainability. lists issues by severity with file:line references.

## bootstrap-python

create a new python project.

```bash
familiar invoke codex bootstrap-python mypackage cli 3.11 mit
```

arguments:

1. package name
2. type: `cli` or `lib`
3. python version (optional, default 3.13)
4. license (optional)

creates pyproject.toml, src layout, readme, ruff/mypy config, and minimal test.

## bootstrap-rust

create a new rust project.

```bash
familiar invoke codex bootstrap-rust myapp bin 1.78 mit
```

arguments:

1. crate name
2. type: `bin` or `lib`
3. msrv (optional)
4. license (optional)

creates crate, readme, formatting/linting setup, and minimal test.

## explain

understand unfamiliar code.

```bash
familiar invoke codex explain "the authentication middleware"
```

identifies code paths, describes behavior, notes edge cases.

## implement-feature

implement a feature from a spec.

```bash
familiar invoke codex implement-feature "add rate limiting to the api endpoints"
```

restates spec, lists files, implements with minimal diffs, adds tests.

## infra-change

plan an infrastructure change.

```bash
familiar invoke codex infra-change "migrate the database to a new region"
```

lists components and impact, proposes rollout/rollback steps, highlights security concerns.

## refactor

restructure code without changing behavior.

```bash
familiar invoke codex refactor "split the monolithic handler into smaller functions"
```

describes current state and proposed changes, ensures tests pass.

## security-review

perform a security review.

```bash
familiar invoke codex security-review
```

identifies trust boundaries, checks for injection risks and secret leakage, lists top risks with mitigations.

## add-ci

add CI workflow for a project.

```bash
familiar invoke codex add-ci github python
familiar invoke codex add-ci gitlab rust
familiar invoke codex add-ci github node
```

arguments:

1. platform: `github` or `gitlab`
2. language: `python`, `rust`, or `node`

creates complete workflow file with lint, typecheck, and test steps.

## audit

comprehensive codebase audit for newcomers.

```bash
familiar invoke codex audit
familiar invoke codex audit security
```

arguments:

1. focus (optional): `architecture`, `security`, `dependencies`, `testing`

examines architecture, dependencies, security surface, technical debt. produces detailed report with recommendations.

## performance

identify and fix performance issues.

```bash
familiar invoke codex performance "the search endpoint"
familiar invoke codex performance src/parser.py memory
```

arguments:

1. target: file, function, or scope to analyze
2. metric (optional): `time`, `memory`, `cpu`, `io`

profiles first, measures baseline, proposes optimizations with tradeoffs, verifies improvement.

## release

prepare a release.

```bash
familiar invoke codex release 1.2.0
familiar invoke codex release minor "Added new API endpoints"
familiar invoke codex release 2.0.0-rc.1
```

arguments:

1. version: number (`1.2.0`), bump type (`major`, `minor`, `patch`), or pre-release (`1.0.0-alpha.1`)
2. description (optional): summary for changelog

updates version files, changelog, provides commit/tag/publish commands.

## placeholders

invocations support these placeholders:

| placeholder | description |
|-------------|-------------|
| `$1`, `$2`, ... | positional arguments |
| `$ARGUMENTS` | all positional arguments joined |
| `{{key}}` | named argument via `--kv key=value` |

example with named arguments:

```bash
familiar invoke codex implement-feature --kv spec="add caching" --kv ttl=300
```
