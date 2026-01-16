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