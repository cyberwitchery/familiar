# changelog

## 0.1.0

initial release.

- `conjure` command to compose system instructions from profiles
- `invoke` command to run agent prompts with arguments
- built-in profiles: core, rust, python, infra, sec
- built-in invocations: add-tests, bootstrap-python, bootstrap-rust, code-review, explain, implement-feature, infra-change, refactor, security-review
- local overrides via `.familiar/` directory
- support for codex and claude agents
