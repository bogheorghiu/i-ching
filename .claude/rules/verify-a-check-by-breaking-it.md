---
paths:
  - "tests/**"
  - ".github/scripts/**"
  - "plugins/*/skills/**/scripts/**"
  - ".githooks/**"
---

# Watch a check fail before you trust it

A test or guard you have never seen fail proves nothing: it may pass because it checks the wrong thing, reads the wrong file, or never runs. Before relying on a new check, break the code it guards on purpose (turn off the rule, drop the field) and confirm the check goes red; then restore the code. Record in the PR which mutations you tried and what caught each. If a mutation stays green, either the check is weak or another layer covers the case; find out which, and write that down.

Each suite runs standalone from the repo root (`python3 <path>` or `bash <path>`), exits non-zero on failure, and is listed by name in a workflow under `.github/workflows/`. A suite not listed there never runs in CI, and a suite that never runs looks exactly like one that passes.
