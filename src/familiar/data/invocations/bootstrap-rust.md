task: bootstrap a new rust crate.

inputs (positional)
- $1 crate_name (required)
- $2 crate_type: bin|lib (required)
- $3 msrv (optional; e.g. 1.78)
- $4 license (optional; e.g. mit, apache-2.0)

preconditions
- if crate_name or crate_type is missing/invalid: ask and stop.
- if target directory exists: ask whether to abort or integrate; do not overwrite by default.

steps
- create crate: `cargo new <crate_name> --<crate_type>`.
- ensure project builds.
- add README.md with: one-line purpose + quickstart commands.
- if msrv provided: encode it (ask preferred mechanism if unclear; do not invent).
- add minimal test if none exists.
- run fmt/clippy/test.

acceptance
- `cargo fmt` succeeds.
- `cargo clippy --all-targets --all-features -- -D warnings` succeeds.
- `cargo test --all-features` succeeds.

output
- unified diff only for files changed/created.
- verification commands (exact).
