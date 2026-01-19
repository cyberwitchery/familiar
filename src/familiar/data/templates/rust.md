# rust

this is a rust project. write idiomatic rust: prefer ownership over references where it simplifies code, use `?` for error propagation, and leverage the type system to make invalid states unrepresentable.

## commands

run these in order after making changes:
```
cargo fmt
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-features
```

## constraints

before making changes, check:
- what is the MSRV? (check `rust-version` in Cargo.toml or CI config)
- does the crate use specific error handling patterns? (thiserror, anyhow, custom)
- is there a workspace? which crates are affected?

STOP and ask before:
- adding a new dependency to Cargo.toml
- changing a public API (pub fn, pub struct fields, trait signatures)
- using `unsafe` for any reason

do not:
- use `unwrap()` or `expect()` in library code (ok in tests and examples)
- swallow errors with `let _ =` without explaining why
- write macros when functions suffice
- ignore clippy lints—fix them or explicitly allow with justification

prefer:
- explicit error types over `Box<dyn Error>` in library code
- small functions that do one thing
- `impl Trait` for return types when the concrete type is an implementation detail
- exhaustive matching over `_ =>` catch-alls

## testing

when adding or modifying code:
1. write a failing test first when feasible
2. test both success paths and error conditions
3. use `#[should_panic]` sparingly—prefer `Result`-returning tests
4. keep tests focused: one behavior per test function

## verification

after changes, run and report results:
```
cargo fmt && cargo clippy --all-targets --all-features -- -D warnings && cargo test --all-features
```
if any command fails, fix the issue before reporting completion.
