task: add tests.

inputs
- $ARGUMENTS (required): module path or symbol name.

preconditions
- if target is missing/unclear: ask what to test and where; stop.

steps
- identify the unit under test and its contract.
- write tests for:
  - happy path
  - one edge case
  - one failure mode
- prefer table/parametrized tests.
- avoid heavy mocking unless necessary; if you mock: explain why.
- run the test suite.

acceptance
- tests are deterministic (no time/network/external dependencies).
- tests are minimal and readable.
- test command succeeds.

output
- unified diff.
- exact test command to run.
