# Fit the request: no speculative structure, no needless specifics

(No `paths:` frontmatter on purpose: this governs any edit, code or prose, so it loads
every session.)

Two failures pull in opposite directions. The same question, asked of every line, catches
both: what does this line buy, and did the request ask for it?

**Over-building.** Configurability nobody asked for, an abstraction around single-use
logic, error handling for a case that cannot occur, a "while I'm here" feature. An LLM
session produces these readily because elaboration is cheap to generate. The cost lands
later: a reviewer has to work out which parts answer the request, and whoever maintains
the extra machinery cannot tell it was never needed.

**Over-specifying.** Tying something to the one case in front of you when nothing is
gained by it: a hardcoded name, path or count where the general form costs no more; a rule
scoped to one file when its reason covers the whole folder; a sentence that names today's
example as if it were the definition. Each one has to be found and edited out once the
thing proves more general, and each one can be missed.

**The test, per line.** For an addition: does the request need it? If not, leave it out.
For a restriction: does narrowing buy something you can name (a check that can fire, a
smaller blast radius, a reader who needs the concrete case)? If not, write the general
form. The two answers do not fight: generality that costs nothing is not speculative, and
specificity that buys something is not needless.

**When the request needs more,** build it and state the why (Rule 1). A stated reason is
what makes an abstraction or a narrowing justified instead of speculative; a bare "keep it
simple" would wrongly forbid the justified case.

**Prior art:** YAGNI ("you aren't gonna need it", Extreme Programming) for the first
failure; the second is its usual misreading, named so it is not mistaken for the rule.

**Sibling:** `no-drive-by-edits` applies the same per-line test to modifications instead of
additions.
