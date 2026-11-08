# No drive-by edits — touch only what the request requires

(No `paths:` frontmatter on purpose — this governs *any* edit, code or prose, so it
loads every session.)

**The failure mode.** "Improving" adjacent code, comments, or formatting while
passing through. The diff stops tracing to intent: review burden grows, regressions
ride in on lines nobody asked to risk, and `git blame` attributes unrelated churn to
your change forever.

**The test, applied per modification:** every changed line traces directly to the
request.

**Boundaries, so the rule doesn't over-fire:**

- **Clean up your own mess — only yours.** Remove imports, variables, and functions
  *your* change orphaned; leave pre-existing dead code in place and *mention* it.
- **Noticing is good; silent fixing is not.** Adjacent bugs, dead code, oddities:
  surface them (a sentence in the report, or an issue) instead of folding them into
  the diff. The reader of the diff is the constituency this rule protects.
- **Match existing style even where you'd choose differently.** Consistency is
  information for the next reader; a style island marks your diff forever.

**Why this deliberately inverts the boy-scout rule.** "Leave the campground cleaner
than you found it" (Clean Code) assumes a trusted editor whose incidental cleanups
are cheap to review. In AI sessions the economics flip: the diff *is* the trust
surface, sessions produce far more edits per day than a human, and unrequested
changes are exactly where unreviewed regressions hide. Same campground, different
risk model — so here, cleanups are *proposed*, not smuggled.

**Sibling:** `no-speculative-structure.md` — the same per-line traceability test
applied to *additions* instead of *modifications*.
