# The filesystem is the index

(No `paths:` frontmatter on purpose: any change can add a list, so this loads every
session.)

**The failure mode.** A hand-kept list of what exists (skills, rules, scripts, files,
counts of any of these) in a README, `AGENTS.md` or a comment. It is right the day it
is written; nothing fires when a file is added, renamed or removed, so it goes stale
while still reading as authoritative, and the next reader trusts it over the tree.

**The test, before writing any list of things in this repository:** can a reader get
it from the directory tree, the file names or the files' own headers? Then do not
write it; say where to look, and make the names and headers carry what the list would
have said.

**The exception is a list a format requires**, such as `marketplace.json` naming each
plugin. Keep such a list, and have a script check it against the tree
(`check_skills.py` fails on a plugin missing from the marketplace), because a machine
reads it and nothing else will notice it drifting.

**Siblings.** `link-to-a-skill-never-describe-it.md` applies the same logic to what a
skill does, and `reserve-prose-for-what-code-cannot-say.md` to what code does; this rule
applies it to what exists.
