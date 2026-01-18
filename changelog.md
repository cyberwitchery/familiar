# changelog

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
