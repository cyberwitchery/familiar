task: bootstrap a new rust crate with best practices.

## inputs

- `crate_name` (required): name of the crate (e.g., `myapp`) set to: $1
- `crate_type` (required): `bin` or `lib` set to: $2
- `msrv` (optional): minimum supported rust version (e.g., `1.75`) set to: $3
- `license` (optional): license identifier (e.g., `MIT`, `Apache-2.0`) set to: $4

## preconditions

STOP and ask if:
- crate_name is missing or invalid (not a valid rust identifier)
- crate_type is not `bin` or `lib`
- the target directory already exists (ask: abort, overwrite, or integrate?)

## what gets created

```
<crate_name>/
├── Cargo.toml          # with metadata, msrv, license if provided
├── README.md           # one-line description + quickstart
├── src/
│   ├── main.rs         # (bin) minimal main with error handling
│   └── lib.rs          # (lib) minimal module with doc comment
└── tests/              # (lib only) integration test placeholder
    └── integration.rs
```

## steps

1. **validate**: confirm inputs are valid and directory doesn't conflict.
2. **create**: run `cargo new <crate_name> --<crate_type>`.
3. **configure**: update Cargo.toml with metadata, msrv, and license.
4. **readme**: create README.md with purpose and quickstart.
5. **test**: add a minimal test if not present.
6. **verify**: run format, clippy, and tests.

## cargo.toml structure

```toml
{{> snippet:rust/Cargo.toml}}
```

## acceptance criteria

all must pass:
```
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-features
```

## output

```
## crate created
<crate_name> (<crate_type>)

## files
<list of files created with brief description>

## changes
<diff of all created/modified files>

## verification
cargo fmt --check && cargo clippy --all-targets --all-features -- -D warnings && cargo test --all-features

## next steps
<suggested next actions: add dependencies, implement features, etc.>
```
