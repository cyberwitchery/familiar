task: review code for quality, correctness, and maintainability.

## inputs

- $ARGUMENTS (optional): file path, function name, or scope to review. if empty, review recent changes or staged diff.

## preconditions

if no target is specified and no recent changes exist:
- ask what to review
- do not review arbitrary code

## review checklist

examine the code for:

**correctness**
- does it do what it claims to do?
- are edge cases handled?
- are error conditions handled properly?
- are there potential null/undefined issues?
- are there hardcoded secrets or credentials?

**clarity**
- is the code easy to understand?
- are names descriptive and consistent?
- is the logic straightforward or needlessly complex?
- are there comments where needed (and only where needed)?

**maintainability**
- is the code modular and testable?
- does it follow project conventions?
- would a new team member understand it?
- is there duplication that should be extracted?

**performance** (only if relevant)
- are there obvious inefficiencies?
- is there unnecessary work in hot paths?

## how to give feedback

- **be specific**: reference file:line, quote the code
- **be actionable**: say what to change, not just what's wrong
- **be proportionate**: don't nitpick style in a bugfix review
- **acknowledge good work**: note well-written code too

## severity levels

- **blocker**: must fix before merge (bugs, security issues, data loss risks)
- **major**: should fix before merge (design issues, missing tests, unclear logic)
- **minor**: consider fixing (style, naming, minor improvements)
- **nit**: optional, take or leave (personal preferences)

## output

```
## scope
<what was reviewed: files, functions, commit range>

## summary
<1-2 sentence overall assessment>

## findings

### blockers
- [file:line] <issue>
  - suggestion: <how to fix>

### major
- [file:line] <issue>
  - suggestion: <how to fix>

### minor
- [file:line] <issue>

### positive
- <what was done well>

## verdict
<approve / request changes / needs discussion>
```
