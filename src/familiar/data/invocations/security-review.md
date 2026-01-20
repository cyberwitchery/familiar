task: perform a security-focused code review.

## inputs

- $ARGUMENTS (optional): file path, function, feature, or scope to review. if empty, review recent changes or the most security-sensitive areas.

## preconditions

STOP and ask if:
- the scope is unclear and you cannot identify an obvious target
- you need context about the threat model or trust boundaries

before starting, identify:
- what user input or external data enters the system
- what sensitive data or operations are involved
- who the potential attackers are and what they might want

## vulnerability checklist

systematically check for:

**injection**
- SQL injection (string concatenation in queries)
- command injection (shell commands with user input)
- path traversal (user input in file paths)
- template injection (user input rendered in templates)
- LDAP/XML injection where applicable
- SSRF (server-side request forgery)

**authentication & authorization**
- missing or bypassable auth checks
- broken session management
- insecure password handling
- missing or weak MFA
- privilege escalation paths

**data exposure**
- secrets in logs, errors, or responses
- sensitive data transmitted unencrypted
- overly verbose error messages
- PII handling violations

**insecure configuration**
- debug modes enabled
- permissive CORS policies
- missing security headers
- default credentials
- unnecessary services exposed

**other**
- unsafe deserialization
- race conditions in security checks
- cryptographic weaknesses
- missing rate limiting

## severity definitions

- **critical**: immediately exploitable, leads to full compromise, data breach, or RCE
- **high**: exploitable with some effort, significant impact (auth bypass, significant data leak)
- **medium**: requires specific conditions, moderate impact (information disclosure, DoS)
- **low**: defense-in-depth issue, minimal direct impact

## output

```
## scope
<what was reviewed>

## threat model
<who might attack this, what they want, what data/operations are at risk>

## findings

### critical
- [file:line] <vulnerability>
  - impact: <what an attacker could do>
  - exploit: <how it could be exploited>
  - fix: <specific remediation>

### high
- [file:line] <vulnerability>
  - impact: <impact>
  - fix: <remediation>

### medium
- [file:line] <issue>
  - fix: <remediation>

### low
- [file:line] <issue>

## recommended fixes
<diffs if implementation requested, otherwise skip>

## verification
<tests or commands to verify each fix>

## areas not covered
<what wasn't reviewed and why>
```
