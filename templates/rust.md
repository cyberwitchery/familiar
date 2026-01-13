# rust profile

## commands (default)
- format: cargo fmt
- lint: cargo clippy --all-targets --all-features -- -D warnings
- test: cargo test --all-features
- build: cargo build --all-features

## rules
- no unsafe without explicit rationale + minimal surface.
- avoid new crates unless strong reason; prefer std + existing deps.
- keep errors structured; use thiserror/anyhow only if already present.
- add tests for parsing/edge cases; prefer table-driven tests.
