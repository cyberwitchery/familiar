# customization

familiar can be extended with local conjurings, invocations, and snippets.

## local overrides

create a `.familiar/` directory in your repository:

```
.familiar/
  conjurings/
    myprofile.md      # new conjuring
    rust.md           # override built-in
  invocations/
    my-task.md        # new invocation
    add-tests.md      # override built-in
  snippets/
    python/
      pyproject.toml  # override built-in snippet
    custom/
      setup.cfg       # new snippet
```

local files take precedence over built-ins.

## writing conjurings

conjurings are markdown files with guidelines for the agent. they should be concise and actionable.

example custom profile for a django project:

```markdown
# django profile

## commands
- test: `python manage.py test`
- migrate: `python manage.py migrate`
- server: `python manage.py runserver`

## rules
- use class-based views for complex logic.
- add migrations for model changes.
- keep views thin, push logic to models/services.
- use django's built-in auth, don't roll your own.
```

save as `.familiar/conjurings/django.md`, then use:

```bash
familiar conjure codex python django
```

## writing invocations

invocations are task prompts with placeholders.

example custom invocation for adding api endpoints:

```markdown
add api endpoint: $ARGUMENTS

requirements:
- follow rest conventions.
- add input validation.
- include error responses.
- add tests for success and failure cases.

output:
- show diffs and curl examples to test.
```

save as `.familiar/invocations/add-endpoint.md`, then use:

```bash
familiar invoke codex add-endpoint "GET /users/{id}"
```

## placeholder reference

| placeholder | description | example |
|-------------|-------------|---------|
| `$1` | first positional arg | `familiar invoke x task foo` → `foo` |
| `$2` | second positional arg | `familiar invoke x task foo bar` → `bar` |
| `$ARGUMENTS` | all args joined | `familiar invoke x task foo bar` → `foo bar` |
| `{{key}}` | named arg | `--kv key=value` → `value` |
| `{{> snippet:path}}` | include a snippet | `{{> snippet:python/pyproject.toml}}` |

## snippet includes

invocations and conjurings can include reusable file templates (snippets) by reference:

```markdown
task: bootstrap a python project

## pyproject.toml structure

```toml
{{> snippet:python/pyproject.toml}}
```
```

in invocations, snippet includes are resolved before placeholder substitution, so snippets can contain `$1`, `{{key}}`, etc. conjurings do no placeholder substitution, so those placeholders are left verbatim there.

see [snippets](snippets.md) for the full list of built-in snippets.

## sharing customizations

to share customizations across repos, you can:

1. create a separate repo with your `.familiar/` conjurings
2. symlink or copy them into projects
3. or fork familiar and add them to the package directly
