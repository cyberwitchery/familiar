# python

this is a python project. follow pep 8, use type hints at module boundaries, and prefer simple, readable code over clever abstractions.

## commands

run these in order after making changes:
```
ruff format .
ruff check .
mypy .
pytest -q
```

## constraints

before making changes, check:
- does the project use `src/` layout or flat layout? match it.
- does the project have existing type hints? match the style.
- does the project use a specific test pattern? follow it.

do not:
- add dependencies to pyproject.toml without approval
- widen public APIs (add parameters, change signatures) without approval
- use `# type: ignore` without explaining why
- leave functions longer than ~30 lines without extracting helpers

prefer:
- explicit types on function signatures and class attributes
- small, pure functions that are easy to test
- pytest parametrization for testing multiple cases
- descriptive names over comments

## testing

when adding or modifying code:
1. write a failing test first when feasible
2. cover the happy path, one edge case, and one error case
3. avoid mocking unless necessary—if you mock, explain why
4. ensure tests are deterministic (no network, no time-dependence)

## verification

after changes, run and report results:
```
ruff format . && ruff check . && mypy . && pytest -q
```
if any command fails, fix the issue before reporting completion.
