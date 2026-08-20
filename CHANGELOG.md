# changelog

## Unreleased

- report a clear error when a conjuring, invocation, or snippet override in `.familiar/` is a directory instead of a file: familiar now names the item it could not read and suggests `familiar list`, instead of leaking a bare `error: [Errno 21] Is a directory`. other read errors are wrapped the same way

## [0.6.0] - 2026-08-07

- `familiar conjure` now expands `{{> snippet:...}}` includes in conjurings (core and selected) instead of writing them verbatim into the generated instruction file, matching the include support invocations already had and the references `familiar lint` already validates
- `familiar lint` now follows snippet includes transitively: a conjuring or invocation that pulls in a snippet whose own body has a broken, cyclic, or too-deeply-nested include is reported at lint time instead of only failing later at `conjure`/`invoke`
- `familiar lint` now checks the snippet collection itself, so a broken or cyclic snippet-to-snippet include is caught even when nothing references it yet
- `familiar lint` now flags undocumented placeholders (`$1`, `$ARGUMENTS`, `{{key}}`) contributed by an invocation's included snippets, not just those written directly in the invocation, matching what the renderer substitutes at invoke time

## [0.5.2] - 2026-07-05

- resolve nested snippet includes: a `{{> snippet:...}}` directive inside an included snippet is now expanded instead of leaking into the rendered prompt verbatim; include cycles (self- or mutually-recursive) raise a clear error naming the chain
- warn on stderr when a `{{key}}` placeholder has no matching `--kv` value instead of silently leaving the literal `{{key}}` in the rendered prompt (positional `$N` placeholders already warned)
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
