refactor: $ARGUMENTS

inputs
- $ARGUMENTS (required): file, function, or code to refactor.

goals:
- improve structure without changing behavior.
- keep diffs minimal and reviewable.

actions:
- describe the current state and proposed changes.
- list files you will touch.
- implement in small steps.
- ensure tests still pass.

output:
- show diffs and how to verify behavior is unchanged.
