# Reserve prose for what code cannot say

(No `paths:` frontmatter on purpose: it governs any change that pairs something run with
prose beside it, so it loads every session.)

**"Code" here means anything that is run**, by a machine or by an agent: a script, a
workflow, a test, and equally a `SKILL.md`, a pattern or a reference file an agent
follows.

**The failure mode.** Prose *beside* code that restates its steps: a comment narrating a
script, a `SKILL.md` repeating what its bundled script already refuses, a test header
listing which tests touch disk. Each copy is true the day it is written, and nothing
fires when the code changes, so it drifts silently and keeps reading as authoritative
while wrong. (Describing a skill from somewhere else, such as a README, is the sibling
rule `link-to-a-skill-never-describe-it.md`.)

## The discipline, in order

1. **First try to make it discernible from the code**: naming, structure, a guard named
   for its invariant, a test whose name states the rule. A comment is what you write after
   trying this and failing.
2. **Prefer changing the code so the sentence is unnecessary.** A comment is a copy, and
   copies rot. Inside functional prose it is different: the reason attached to an
   instruction is part of what the agent runs (Rule 1), so it stays.
3. **When it cannot live in code, write it down; never abstain.** Why X over Y, an
   incident, a trade-off, a decision that binds a future reader: code cannot carry these.
   This rule is not "fewer comments".
4. **Check it independently.** Give the code without the comment to a fresh reader who did
   not write it. Can they say what the comment says? Then it duplicates; cut it or push it
   into the code. If not, the comment has earned its place.
5. **Sometimes the right home is one separate document** for the few things code cannot
   hold (rationale, incidents, trade-offs). Every addition to it faces the same test.

## Seam with Rule 1 — state the why

Rule 1 in `AGENTS.md` demands that the why exist; this rule governs where it lives: in the
code first, then a comment, then a separate document, never nowhere.

**Prior art:** "comments explain why, not what" (self-documenting code; DRY across the
code-prose boundary), extended: even the why is first attempted in code, and an
independent reader decides when it can't be.

**Siblings.** `link-to-a-skill-never-describe-it.md` covers prose at a distance;
`no-speculative-structure.md` and `no-drive-by-edits.md` govern what gets added or changed.
