# python profile

## commands (default)
- format: black
- lint: black --check
- type: mypy .
- test: pytest -q

## rules
- keep functions small; push complexity into pure helpers.
- add tests for boundary cases; use pytest parametrization.
- do not widen public apis casually; keep backwards compatible.
- prefer explicit types at module boundaries.
