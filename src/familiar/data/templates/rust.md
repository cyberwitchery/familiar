# rust profile

## commands
- format: cargo fmt
- lint: cargo clippy --all-targets --all-features -- -d warnings
- test: cargo test --all-features
- build: cargo build --all-features

## rules
- do not introduce new crates unless you ask first.
- avoid unsafe. if unavoidable: justify + minimize surface + add tests.
- prefer explicit error types; do not swallow errors.
- prefer small, composable functions; avoid clever macros.
- do not change public apis without explicit approval.

## workflow
- locate existing patterns in the crate and follow them.
- write or update tests first when feasible.
- keep diffs minimal; avoid reformatting unrelated code.
- ensure msrv/toolchain constraints are respected; ask if unknown.

## output
- show a unified diff.
- list the exact cargo commands to verify (fmt/clippy/test).
