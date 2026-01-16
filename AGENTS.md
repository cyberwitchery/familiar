# agent core

## intent
- smallest correct change. no drive-by refactors.
- keep existing conventions unless asked.

## workflow
- restate task in 1-2 lines.
- list files you will touch before editing.
- implement in small steps.
- run format + lint + tests (or say exactly why you cannot).
- finish with: what changed, why, how to verify.

## output
- show diffs or exact file contents for edits.
- include commands to reproduce.

## guardrails
- ask before adding dependencies, new services, migrations, or changing public apis.
- never print secrets. stop if you suspect secret access is needed.
- prefer local fixes over big rewrites.

# python profile

## commands (default)
- format: ruff format
- lint: ruff check
- type: mypy .
- test: pytest -q

## rules
- keep functions small; push complexity into pure helpers.
- add tests for boundary cases; use pytest parametrization.
- avoid widening public APIs casually; keep backwards compatible.
- prefer explicit types at module boundaries.

- do not add new dependencies unless asked or clearly necessary.
