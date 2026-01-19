task: implement a feature from a specification.

## inputs

- {{spec}} (required): feature specification as a file path or pasted text.

## preconditions

STOP and ask if:
- no spec is provided
- the spec is ambiguous or contradictory
- acceptance criteria are missing or unclear
- implementation would require adding dependencies
- implementation would require changing public APIs

before coding:
1. restate the spec in your own words (1-2 sentences)
2. list explicit acceptance criteria—if none exist, propose them and wait for approval
3. identify files you will create or modify

## constraints

- **minimal implementation**: implement exactly what's specified, nothing more.
- **no new dependencies**: if a library would help, ask first.
- **no API changes**: if the public interface must change, ask first.
- **test first**: write a failing test before implementing (when feasible).

## steps

1. **understand**: read the spec and restate it to confirm understanding.
2. **clarify**: if anything is ambiguous, ask up to 3 targeted questions, then stop.
3. **plan**: list acceptance criteria and files to change.
4. **test**: write failing tests that will pass when the feature works.
5. **implement**: write the minimum code to make tests pass.
6. **verify**: run format, lint, type check, and tests.
7. **review**: check that implementation matches spec exactly.

## definition of done

- [ ] all acceptance criteria are met
- [ ] all existing tests still pass
- [ ] new tests cover happy path and one edge case
- [ ] no new dependencies added without approval
- [ ] no public API changes without approval
- [ ] code follows project conventions

## output

```
## spec summary
<1-2 sentence restatement>

## acceptance criteria
1. <criterion>
2. <criterion>
3. <criterion>

## files changed
- <path>: <what changes>
- <path>: <what changes>

## implementation

### tests
<diff of new tests>

### code
<diff of implementation>

## verification
<commands to run>

## notes (optional)
<assumptions made, alternatives considered>
```
