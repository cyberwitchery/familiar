# changelog

## unreleased

- fix lint false-negative for undocumented named placeholders: substring check no longer matches inside other words (e.g. `{{name}}` was silently accepted when only `filename` appeared in inputs)

## [0.5.1] - 2026-05-22

- gracefully skip unreadable files (bad encoding, permission denied) when listing conjurings, invocations, and snippets instead of crashing
- improve error messages for permission denied and encoding errors when reading local conjurings, invocations, and snippets
- warn when git worktree removal fails instead of silently ignoring the error
- show actionable error messages when writing instruction, skill, or subagent files fails

## [0.5.0] - 2026-04-26

- fix worktree leak: clean up git worktree on agent failure instead of leaving stale worktrees
- warn when instruction file copy fails during worktree setup instead of silently swallowing the error
- add `--version` flag to CLI

## [0.4.0] - 2026-02-16

- add skills and subagents
- add SBOM generation for releases

## [0.3.1] - 2026-01-30

- add auto mode
- change argument order for `invoke`

## [0.3.0] - 2026-01-29

- add dry run mode
- add snippets

## [0.2.1] - 2026-01-29

- add bandit to dev dependencies
- rename profiles to conjurings consistently throughout

## [0.2.0] - 2026-01-24

- add worktree support for `invoke` (fixes #10)

## [0.1.2] - 2026-01-20

- refactor agent definitions
- add initial SLP version of conjurings and invocations (#9)

## [0.1.1] - 2026-01-19

- minor consistency fixes

## [0.1.0] - 2026-01-19

- first stable release

## [0.0.5] - 2026-01-19

- improve invocations and conjurings
- minor cleanups

## [0.0.4] - 2026-01-19

- add `lint`, `simplify`, `read` subcommands
- add tests for lint CLI

## [0.0.3] - 2026-01-18

- add `conjurings` subcommand (fixes #5)
- add better error messages and debug output (closes #2, #7)

## [0.0.2] - 2026-01-18

- add `list` command (closes #3)
- add test suite (closes #1)
- drop python 3.9 support

## [0.0.1] - 2026-01-16

- initial release
