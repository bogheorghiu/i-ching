# Link to a skill; never describe it outside itself

(No `paths:` frontmatter on purpose: a description of a skill can turn up in any file, so
this loads every session.)

**The failure mode.** A README, `AGENTS.md`, `REVIEW.md`, a rule file or a PR body that
says what a skill does or which rules it follows. It is true when written; nothing fires
when the skill changes, so it goes on reading as authoritative after it has gone wrong,
and a reader trusts it over the skill.

**The test:** outside the skill, say what it is for and where it is. Everything about what
it does lives in its own `SKILL.md` and the files it references. If a sentence would need
editing when the skill changes, it belongs in the skill, not here.

**The exception is a description a format requires**: the frontmatter `description`, a
plugin manifest, a `marketplace.json` entry, a Directory listing. Keep each to what the
skill is for and when to use it, not how it works.

**Sibling.** `filesystem-is-the-index.md` applies the same logic to what exists;
`reserve-prose-for-what-code-cannot-say.md` to prose beside the code it describes.
