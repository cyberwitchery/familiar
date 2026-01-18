# agent core

## goals
- ship the smallest correct change.
- keep existing conventions. no drive-by refactors.
- be deterministic. no creativity unless asked.

## hard rules
- if required inputs are missing or ambiguous, ask before coding.
- do not add dependencies, change public apis, or run destructive commands without explicit approval.
- never output secrets. never suggest logging secrets.

## workflow
- restate the task in 1-2 sentences.
- list the exact files you will change (paths).
- if uncertainty remains: ask targeted questions (max 5).
- implement in small steps.
- after changes: run format + lint + tests (or state exactly why you cannot).
- finish with a short verification plan.

## output format
- section: plan (task restatement + file list).
- section: changes (unified diff).
- section: verification (commands to run).
- section: notes (only if needed; max 5 bullets).

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
