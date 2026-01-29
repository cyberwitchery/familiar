# contributing

thanks for your interest in familiar.

## setup

```bash
git clone https://github.com/cyberwitchery/familiar.git
cd familiar
make dev
```

## development workflow

```bash
make lint    # run ruff + mypy
make test    # run pytest
make coverage # run tests with coverage report
```

## adding a conjuring

1. create `src/familiar/data/conjurings/<name>.md`
2. use lowercase kebab-case for the filename
3. start with a heading describing the conjuring
4. keep it concise and actionable

example structure:

```markdown
# <name> conjuring

## commands
- test: `<test command>`
- build: `<build command>`

## rules
- rule one.
- rule two.
```

## adding an invocation

1. create `src/familiar/data/invocations/<name>.md`
2. use lowercase kebab-case for the filename
3. use placeholders for dynamic content:
   - `$1`, `$2`, ... for positional args
   - `$ARGUMENTS` for all args joined
   - `{{key}}` for named args via `--kv key=value`

example structure:

```markdown
<task description>: $ARGUMENTS

requirements:
- requirement one.
- requirement two.

output:
- what to produce.
```

## style guide

- all prose is lowercase (except code/proper nouns)
- be concise - prompts should be scannable
- use imperative mood ("add tests" not "adding tests")
- no trailing punctuation on list items unless they're full sentences

## pull requests

- run `make lint` and `make test` before submitting
- keep commits focused and atomic
- update changelog.md for user-facing changes
