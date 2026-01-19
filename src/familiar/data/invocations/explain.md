task: explain code or concepts.

## inputs

- $ARGUMENTS (required): file path, function name, code snippet, or concept to explain.

## preconditions

if the target is ambiguous or cannot be located:
- ask for clarification (file path, function name, or paste the code)
- do not guess or explain something different

## steps

1. **locate**: find the relevant code. state the file path(s) and line numbers.
2. **context**: identify what calls this code and what it depends on.
3. **explain**: describe what it does, how it works, and why it's designed this way.
4. **highlight**: note any non-obvious behavior, edge cases, or potential gotchas.

## what makes a good explanation

- starts with a one-sentence summary
- uses concrete references (file:line)
- explains the "why" not just the "what"
- notes assumptions and constraints
- avoids unnecessary jargon

## output

```
## summary
<one-sentence description of what this does>

## location
<file paths and line numbers>

## explanation
<detailed explanation with references>

## notes
<edge cases, assumptions, or non-obvious behavior>
```
