# snippets

snippets are reusable file templates that invocations can include by reference. they prevent drift and prompt bloat by keeping canonical file bodies in one place.

## built-in snippets

### python

| snippet | description |
|---------|-------------|
| `python/pyproject.toml` | canonical pyproject.toml with ruff, mypy, pytest |
| `python/github-ci.yml` | github actions workflow (uv-based) |
| `python/gitlab-ci.yml` | gitlab ci config (uv-based) |

### rust

| snippet | description |
|---------|-------------|
| `rust/Cargo.toml` | canonical Cargo.toml with metadata |
| `rust/github-ci.yml` | github actions workflow (fmt, clippy, test) |
| `rust/gitlab-ci.yml` | gitlab ci config (fmt, clippy, test) |

### node

| snippet | description |
|---------|-------------|
| `node/github-ci.yml` | github actions workflow (lint, typecheck, test) |
| `node/gitlab-ci.yml` | gitlab ci config (lint, typecheck, test) |

## include syntax

use `{{> snippet:path}}` inside invocations to include a snippet:

```markdown
## pyproject.toml structure

```toml
{{> snippet:python/pyproject.toml}}
```
```

includes are resolved before placeholder substitution, so snippets can contain `$1`, `$ARGUMENTS`, and `{{key}}` placeholders.

a snippet may itself include other snippets; nested includes are expanded recursively. include cycles (a snippet that includes itself, directly or transitively) raise an error naming the chain rather than looping forever.

## listing snippets

```bash
familiar list snippets
familiar list snippets -v
```

## local overrides

place snippet files under `.familiar/snippets/` to override built-ins:

```
.familiar/snippets/python/pyproject.toml
```

the same "local wins" precedence applies as with conjurings and invocations.

## linting

`familiar lint` validates snippet references:

- **error** if an invocation references a snippet that doesn't exist
