bootstrap a new rust project.

arguments:
- crate name: $1
- type: $2 (bin|lib)
- msrv: $3 (optional)
- license: $4 (optional)

actions:
- create the crate using cargo.
- add a minimal readme (what it does, how to run).
- set up formatting and linting if missing.
- add a minimal test.

acceptance:
- `cargo fmt`, `cargo clippy`, and `cargo test` succeed.

output:
- show diffs and exact commands.
