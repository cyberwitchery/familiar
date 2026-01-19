task: add tests for existing code.

## inputs

- $ARGUMENTS (required): file path, function name, class name, or module to test.

## preconditions

STOP and ask if:
- the target is unclear or cannot be located
- you're unsure what behavior to test
- the code has no clear contract or expected behavior

before starting:
- read the code to understand its contract
- check if tests already exist (don't duplicate)
- identify the testing framework used in the project

## constraints

- **match project conventions**: use the same test framework, file locations, and naming patterns.
- **no behavior changes**: you're adding tests, not fixing bugs (note bugs separately).
- **minimal mocking**: only mock external dependencies; prefer real objects when possible.

## what to test

write tests covering:
1. **happy path**: the main success scenario
2. **edge case**: boundary conditions, empty inputs, large inputs
3. **error case**: invalid inputs, expected failures

## test quality checklist

each test should be:
- [ ] **deterministic**: no flakiness from time, network, or random values
- [ ] **isolated**: can run independently of other tests
- [ ] **fast**: no unnecessary I/O or sleeps
- [ ] **readable**: clear what's being tested and why
- [ ] **focused**: one behavior per test

## steps

1. **locate**: find the code to test and understand its contract.
2. **check**: verify no duplicate tests exist.
3. **plan**: list the test cases you will write.
4. **write**: implement tests, preferring parametrized/table-driven style.
5. **run**: execute the test suite and confirm all tests pass.

## output

```
## unit under test
<file:function or class being tested>

## test cases
1. <test name>: <what it verifies>
2. <test name>: <what it verifies>
3. <test name>: <what it verifies>

## changes
<diff of new test file or additions>

## verification
<exact test command>

## notes (optional)
<bugs noticed, edge cases not covered, etc.>
```
