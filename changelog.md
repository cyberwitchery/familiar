# changelog

## unreleased

- add release SBOM generation and upload (CycloneDX)
- add `--save-skill` and `--skill-name` options to `invoke` to export invocations as reusable Claude/Codex skills
- add `--save-subagent` and `--subagent-name` options to `conjure` to export composed conjurings as reusable Claude/Codex subagents

## 0.3.1

- **auto mode**: added `--auto` flag to `invoke` command to skip agent permission prompts (`--full-auto` for codex, `--dangerously-skip-permissions` for claude).
- **improved invocation arguments**: invocation argument descriptions now use `set to: $N` suffix format for better agent prompt performance.

## 0.3.0

- **snippets**: added reusable file templates ("snippets") that invocations can include via `{{> snippet:path}}`. built-in snippets for python, rust, and node CI workflows and project configs. local overrides in `.familiar/snippets/`. `familiar list snippets` to discover available snippets. `familiar lint` validates snippet references.
- **refactored scaffold invocations**: `bootstrap-python`, `bootstrap-rust`, and `add-ci` now use snippet includes instead of embedding file bodies directly.
- **dry-run**: added `--dry-run` flag to `invoke` command to print the rendered prompt without running the agent.
- **bandit**: added bandit security linter to CI and dev dependencies.

## 0.2.1

- **renamed templates to conjurings**: internal `data/templates/` directory renamed to `data/conjurings/`, matching the user-facing terminology. local overrides now go in `.familiar/conjurings/`. linter plugin entry point is now `familiar.linters.conjurings`.

## 0.2.0

- **git worktrees**: added `--worktree` flag to `invoke` command. This allows running agents in a separate, isolated git worktree to avoid interference with local changes.
- **enhanced testing**: improved test coverage for CLI and worktree management.
- **documentation**: added worktree usage details to README and CLI reference.

## 0.1.2

- **new conjurings**: `frontend` (react), `docs` (documentation), `data` (data engineering)
- **new invocations**: `add-ci` (github/gitlab workflows), `audit` (codebase audit), `performance` (profiling and optimization), `release` (version bump and changelog)
- **documentation**: updated docs/conjurings.md and docs/invocations.md with new templates

## 0.1.1

- **improved placeholder substitution**: now uses a single-pass regex to prevent unintentional secondary expansion of user-provided content
- **refined linter**: placeholder documentation checks now prioritize `## inputs` and `## arguments` sections for better accuracy
- **improved claude agent**: now uses the repository root as the working directory for more consistent behavior
- **git agnostic**: clarified that the tool works in any directory, falling back to the current directory if `.git` is not found
- **internal refactoring**: consolidated linting logic to improve maintainability

## 0.1.0

- **plugin architecture**: extensible via Python entry points
  - agent plugins: add new agents without modifying familiar core
  - linter plugins: add custom lint rules for templates and invocations
  - built-in agents (codex, claude) migrated to the plugin system
  - graceful error handling for plugin load failures
- added `py.typed` marker for PEP 561 compatibility
- see [plugin docs](https://familiar.readthedocs.io/en/latest/plugins/) for details

## 0.0.5

- rewrote all conjurings and invocations for better LLM prompting
  - added explicit role framing and prioritized constraints
  - standardized STOP conditions and output formats
  - added checklists and structured workflows
- linter now recognizes markdown heading format (`## inputs`)
- fixed case-sensitivity bug in placeholder documentation check
- improved error handling: `get_agent` now raises proper exceptions
- code cleanup: consolidated duplicate printing logic in `list` command

## 0.0.4

- `lint` command to validate templates and invocations
- standardized invocation structure with recommended sections
- improved placeholder documentation detection in linter
- simplified architecture: removed config file management
- removed `conjurings` command (was show/set/reset)

## 0.0.3

- `conjurings` command to manage saved conjurings (show/set/reset)
- improved error messages with actionable hints
- added `--debug` flag to show full tracebacks
- added examples to `--help` output
- added Makefile for common dev tasks
- added CONTRIBUTING.md

## 0.0.2

- `list` command to discover available conjurings and invocations (lists both by default)
- renamed "profiles" to "conjurings" throughout

## 0.0.1

initial release.

- `conjure` command to compose system instructions from conjurings
- `invoke` command to run agent prompts with arguments
- built-in conjurings: core, rust, python, infra, sec
- built-in invocations: add-tests, bootstrap-python, bootstrap-rust, code-review, explain, implement-feature, infra-change, refactor, security-review
- local overrides via `.familiar/` directory
- support for codex and claude agents
