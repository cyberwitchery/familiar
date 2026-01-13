# security profile

## always do
- identify trust boundaries + attacker-controlled inputs.
- confirm authn/authz expectations (who can do what).
- check for secret leakage (logs, errors, traces, metrics).
- validate input early; fail closed; secure defaults.

## never do
- weaken tls/crypto settings “temporarily”.
- add debug logging of tokens/headers/payloads containing secrets.
- introduce permissive wildcard policies without justification.

## deliverables
- list top risks + mitigations (bullets).
- propose the smallest diff that closes the biggest risk first.
