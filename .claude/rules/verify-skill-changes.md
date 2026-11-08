---
paths:
  - "plugins/*/skills/**"
---

# Verify a skill change at the level it needs, and say which level ran

A skill is code that a model executes, so a change to its prose can break a run as surely as a code change. CI cannot see that: it checks structure and scripts, not whether an agent reading the new text still reads the hexagram the script cast, or quotes the text it claims to.

Three levels, cheapest first:

1. **Structural.** The checks `skills-ci.yml` runs, locally or in CI. Enough for a typo or a source entry backed by a run.
2. **Blind review.** A fresh agent with no context from your session reads the whole skill folder against a bar written down before it starts: BLOCKING means following the files would plausibly give the user a wrong result, break a law or a service's policy, or fail the run. Ask open questions ("what does an agent do at step 4?"), never "confirm that step 4 now asks", because a reviewer told the expected answer finds it. Needed for any change to `SKILL.md`, a pattern, or a reference file that states law or a service's policy.
3. **Live run.** The skill end to end on a real case (here, a real reading in a fresh agent with no other context). The only level that shows whether the world still behaves as the files claim: actors, schemas, prices, a maker's page.

In the PR, name the highest level you ran and what it could not see. "CI is green" for a prose change means level 1 only. A reviewer's disagreement with you goes to the owner as it stands; do not quietly reconcile it.
