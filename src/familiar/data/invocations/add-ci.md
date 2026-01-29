task: add continuous integration workflow for linting, testing, and static analysis.

## inputs

- $1 `platform` (required): CI platform (`github` or `gitlab`)
- $2 `language` (required): primary language (`python`, `rust`, `node`)

## preconditions

STOP and ask if:
- platform is not `github` or `gitlab`
- language is not `python`, `rust`, or `node`
- CI configuration already exists (ask: replace, merge, or abort?)
- the project structure doesn't match expectations (no pyproject.toml, Cargo.toml, or package.json)

## what gets created

### github actions
```
.github/
└── workflows/
    └── ci.yml
```

### gitlab ci
```
.gitlab-ci.yml
```

## steps

1. **detect**: check for existing CI and project structure
2. **create**: write workflow file for the language
3. **verify**: validate workflow syntax if possible

---

## python workflows

### github actions (python)

```yaml
{{> snippet:python/github-ci.yml}}
```

### gitlab ci (python)

```yaml
{{> snippet:python/gitlab-ci.yml}}
```

---

## rust workflows

### github actions (rust)

```yaml
{{> snippet:rust/github-ci.yml}}
```

### gitlab ci (rust)

```yaml
{{> snippet:rust/gitlab-ci.yml}}
```

---

## node workflows

### github actions (node)

```yaml
{{> snippet:node/github-ci.yml}}
```

### gitlab ci (node)

```yaml
{{> snippet:node/gitlab-ci.yml}}
```

---

## output

```
## CI configured
platform: <github|gitlab>
language: <python|rust|node>

## file created
<path to workflow file>

## workflow contents
<the complete workflow file>

## next steps
- push to trigger the workflow
- verify scripts exist in package.json / pyproject.toml if needed
- add secrets if using protected actions
```
