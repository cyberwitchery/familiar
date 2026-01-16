bootstrap a new python project.

arguments:
- package name: $1
- type: $2 (cli|lib)
- python version: $3 (optional, default 3.9)
- license: $4 (optional)

actions:
- create pyproject.toml with metadata.
- set up src layout.
- add a minimal readme.
- configure ruff and mypy.
- add a minimal test.

acceptance:
- `ruff check`, `mypy .`, and `pytest` succeed.

output:
- show diffs and exact commands.
