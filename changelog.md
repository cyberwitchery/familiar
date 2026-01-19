# changelog

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
