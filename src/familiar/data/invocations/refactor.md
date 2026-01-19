task: refactor code without changing behavior.

## inputs

- $ARGUMENTS (required): file path, function name, or description of code to refactor.

## preconditions

STOP and ask if:
- the target code is unclear or cannot be located
- there are no existing tests covering the code
- the refactoring would require changing public APIs

before starting, verify:
- existing tests pass (run them first)
- you understand what the code currently does

## constraints

- **behavior must not change**: the code must produce identical outputs for identical inputs.
- **keep diffs minimal**: only touch what's necessary for the refactoring.
- **no drive-by fixes**: don't fix unrelated issues you notice—note them separately.
- **no new dependencies**: refactoring should not require new libraries.

## steps

1. **understand**: read the code and document its current behavior.
2. **plan**: describe what you will change and why it improves the code.
3. **verify baseline**: run existing tests to confirm they pass.
4. **refactor**: make changes in small, atomic steps.
5. **test**: run tests after each step to catch regressions immediately.
6. **review**: present the before/after comparison.

## what makes a good refactoring

- improves readability, maintainability, or performance
- each change is small enough to review in isolation
- the git history would tell a clear story
- no behavior changes sneak in

## output

```
## goal
<what this refactoring improves and why>

## files changed
<list of file paths>

## changes

### step 1: <description>
<diff>

### step 2: <description>
<diff>

## verification
<test command and expected result>

## notes (optional)
<unrelated issues noticed but not addressed>
```
