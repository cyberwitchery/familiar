# python profile

## commands
- format: ruff format
- lint: ruff check
- type: mypy .
- test: pytest -q

## rules
- keep functions small; push complexity into pure helpers.
- write tests for edge cases; prefer pytest parametrization.
- do not widen public apis without explicit approval.
- do not add new dependencies without explicit approval.
- prefer explicit types at module boundaries.

## workflow
- follow existing project structure and naming.
- add tests that fail before the fix/feature (when possible).
- keep diffs minimal; avoid unrelated cleanup.
- run format + lint + type + tests, or say exactly why you cannot.

## output
- show a unified diff.
- list the exact commands to verify (ruff/mypy/pytest).
