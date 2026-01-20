task: conduct a comprehensive audit of the codebase for deep understanding.

## inputs

- $1 `focus` (optional): area to emphasize (`architecture`, `security`, `dependencies`, `testing`). default: all.

## purpose

not a review of recent changes—a full examination to understand how it works, where the risks live, and what a newcomer needs to know. take as much time as needed.

## audit areas

### 1. architecture
- major components and how they communicate
- system boundaries (DBs, external APIs, filesystem)
- patterns in use (layered, hexagonal, event-driven, etc.)

### 2. entry points and data flow
- where execution starts
- where user input enters
- how data flows through layers
- where data exits (responses, writes, side effects)

### 3. domain model
- key entities and their relationships
- where business logic lives

### 4. dependencies
- external: list with versions, flag outdated/vulnerable
- internal: circular dependencies, god modules

### 5. testing
- coverage and types (unit, integration, e2e)
- what's NOT tested that should be

### 6. security
- where untrusted input enters
- auth/authz implementation
- secrets handling
- injection risks

### 7. error handling
- consistency of error handling
- logging and observability

### 8. configuration
- how environments differ
- secrets management

### 9. build and deploy
- build process, deployment, migrations, rollback

### 10. technical debt
- TODOs/FIXMEs, dead code, duplication, outdated patterns

## depth guidelines

- read actual code, not just file names
- trace real execution paths
- prioritize: auth, money, sensitive data, hot paths, high complexity

## output

```
## audit: <project>

## summary
<3-5 sentences: what it is, what's good, what's concerning>

## architecture
<components, patterns, boundaries>

## critical paths
<traced execution for key flows>

## dependencies
| name | version | status | notes |
|------|---------|--------|-------|

## security surface
<entry points and risks>

## technical debt
### high priority
- [file:line] <issue>

## risks
- <risk>: <likelihood>, <impact>

## recommendations
### immediate
### short-term
### long-term
```
