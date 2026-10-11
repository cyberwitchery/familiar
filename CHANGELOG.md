# changelog

## Unreleased

- `familiar lint` now ends an invocation's `inputs` section where the next section starts in both layouts it accepts: under a bare `inputs` label, as in the recommended invocation structure, a placeholder used only under a later label such as `steps` is now reported as undocumented instead of always passing; under a `## inputs` heading, a `#` line that is not a heading, such as `#tag`, no longer cuts the section short and makes the placeholders documented after it look undocumented, while a heading indented by up to three spaces now ends it
- `familiar list`, `lint`, `invoke` and `conjure` now agree on what in `.familiar/` overrides a builtin, and never open anything but a regular file: a directory, FIFO, socket or device where a conjuring, invocation or snippet file belongs is listed as `(local, unreadable)` and reported by `lint` under its `.familiar/` path instead of the builtin's, where a FIFO used to hang `lint`, `invoke` and `conjure`; an unsearchable directory or an over-long path no longer aborts `list` and `lint` on Python 3.10–3.13; and `list` prints a file name that is not valid UTF-8 with `\xNN` escapes instead of failing
- `familiar lint` no longer reports a conjuring or invocation that starts with a blank line as `template is empty` / `invocation is empty`, an error that also skipped every other check on the file: the heading and `task:` checks now read the first non-blank line and point their warnings at it, and `familiar list -v` describes a conjuring, invocation, or snippet by that line instead of showing an empty description
- `familiar lint` and `familiar list` no longer silently skip a conjuring, invocation, or snippet in `.familiar/` that cannot be read (not valid UTF-8, permission denied, a dangling symlink): `lint` reports it by name with the reason, `list` marks it `(local, unreadable)`, and an include of such a snippet is reported with the reason instead of as `snippet not found`
- `familiar invoke` now keeps every `--kv` pair when the flag is repeated, as in `--kv spec="add caching" --kv ttl=300`, instead of silently dropping all but the last flag's pairs and leaving their `{{key}}` placeholders unfilled

## [0.6.1] - 2026-09-06

- report a clear error when a conjuring, invocation, or snippet override in `.familiar/` cannot be read — a directory where a file is expected, a name too long for the filesystem, an unreadable parent directory: familiar now names the item it could not read and suggests `familiar list`, instead of leaking a bare `error: [Errno 21] Is a directory`
- a broken symlink override (dangling, or looping back on itself) is now reported by name instead of being silently skipped in favour of the packaged builtin
- `familiar lint` no longer reports a placeholder as undocumented when the inputs section contains a fenced code example: a `#` comment inside a code fence is no longer mistaken for the heading that ends the section
- `familiar lint` now warns about an undocumented `$1` in an invocation that also uses `$10`; documenting only the longer placeholder no longer counts as documenting the shorter one
- `familiar lint` now ignores `inputs`/`output` headings that appear inside a fenced code block: an invocation whose only such heading sits in a code example is reported as missing the section, and a fenced example heading no longer makes placeholders that are documented further down the file look undocumented
- `familiar lint` no longer reports a missing `inputs`/`output` section because of a code fence nested under a bullet or inside a block quote: fences are now measured against the container they sit in, the way commonmark measures them, so an example fence whose closing marker is indented under its bullet no longer swallows the rest of the file
- `familiar lint` no longer mistakes a code fence written inside a raw HTML block for a real fence: an example fence wrapped in `<details>` or `<div>` with no blank line between them is part of the HTML, the way commonmark reads it, so the `inputs`/`output` headings that follow it are still found

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
