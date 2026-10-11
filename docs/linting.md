# linting

`familiar lint` validates conjurings and invocations. it catches common issues before they cause problems at runtime.

## usage

```bash
familiar lint [--into <path>] [--errors-only]
```

| option | description |
|--------|-------------|
| `--into` | target repository path (default: current directory) |
| `--errors-only` | show only errors, suppress warnings |

## exit codes

| code | meaning |
|------|---------|
| 0 | all checks passed (warnings are ok) |
| 1 | one or more errors found |

## rules

### conjurings

conjurings in `.familiar/conjurings/*.md` or built-ins.

| level | rule |
|-------|------|
| error | file is empty |
| warning | first non-blank line is not a markdown heading (`# ...`) |

### invocations

invocations in `.familiar/invocations/*.md` or built-ins.

| level | rule |
|-------|------|
| error | file is empty |
| warning | first non-blank line is not a task verb (see below) |
| warning | missing `inputs` or `arguments` section |
| warning | missing `output` or `deliverables` section |
| warning | placeholder `{{name}}` not documented in content |
| warning | placeholder `$N` not documented in content |

**recognized task verbs:** `task`, `explain`, `review`, `analyze`, `check`, `audit`, `describe`, `create`, `generate`, `refactor`, `bootstrap`, `implement`, `add`, `fix`

**recognized input sections:** `inputs`, `input`, `arguments`, `argument` (with optional parenthetical like `inputs (positional)`)

**recognized output sections:** `output`, `outputs`, `deliverable`, `deliverables`

## placeholder detection

the linter checks that placeholders are documented in the file. if the file has an `inputs` or `arguments` section, only that section is searched; otherwise the whole file is. a `## inputs` section ends at the next heading, and a heading needs a space after its `#`s, so a line like `#tag` does not end it. a bare `inputs` label's section ends at the next heading or at the next paragraph outside a list item or block quote, which is where the next bare label (`steps`, `output`, ...) starts, so a loose list and anything indented under its items stay in the section. nothing inside a code fence ends a section, and without a later heading or paragraph the section runs to the end of the file. snippet includes are expanded first, so a placeholder that only appears inside an included snippet is still checked.

**positional placeholders:** `$1`, `$2`, ..., `$ARGUMENTS`

the linter looks for patterns like:
- `name: $1` (description before placeholder)
- `$1 crate_name` (placeholder followed by name)
- `$1 (required)` (placeholder with modifier)

**named placeholders:** `{{name}}`

the linter checks if the placeholder name appears elsewhere in the content (likely in an inputs section).

## examples

```bash
# lint everything in current repo
familiar lint

# lint specific repo
familiar lint --into /path/to/repo

# ci mode: fail only on errors
familiar lint --errors-only
```

## recommended invocation structure

```markdown
task: brief description of what this does

inputs
- $1 arg_name (required): description
- {{named_arg}} (optional): description

preconditions
- condition to check before starting

steps
- step 1
- step 2

acceptance
- criterion 1
- criterion 2

output
- what the agent should produce
```

this structure is not enforced strictly, but the linter will warn if key sections are missing.
