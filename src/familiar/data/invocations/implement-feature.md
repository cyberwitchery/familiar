task: implement a feature from a spec.

inputs (named)
- {{spec}} (required): file path in repo OR pasted spec text.

preconditions
- if spec is empty: ask for a file path or pasted spec; stop.
- if spec is ambiguous or missing acceptance criteria: ask up to 5 clarifying questions; stop.

steps
- restate the spec in 1-2 sentences.
- extract explicit acceptance criteria (bullets). if none: propose criteria and ask for confirmation; stop.
- list files you will change (paths).
- write failing tests first when feasible.
- implement the smallest change that satisfies the criteria.
- run format/lint/type/tests.

acceptance
- all existing tests pass.
- new tests cover the main path + one edge case.
- no new deps or public api changes unless explicitly approved.

output
- plan (restatement + file list).
- unified diff.
- verification commands.
