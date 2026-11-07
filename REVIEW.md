# Review instructions

This repository ships Agent Skills: prose and small scripts that other people's agents execute, with those people's trust. A sentence in a `SKILL.md` is code. Review it as code whose failure mode is an agent confidently doing the wrong thing.

Read `AGENTS.md` and the files in `.claude/rules/` first; they state the repository's rules and why each exists. Review the diff together with the PR body: several checks below are about what the body states. This file says what to flag and how hard. Important here means the same as BLOCKING in the rule `verify-skill-changes`; a rule is named by its file in `.claude/rules/`.

## What Important means here

Reserve Important for findings where following the changed files would plausibly:

- **give the user a wrong result stated as fact**: a load-bearing claim (a figure, a standard, a law, a product's contents, a service's policy) with no source and no evidence tag, or a tag the cited source does not support;
- **act without the user's consent**: a network call, a write outside the skill folder, or anything the plugin README says the plugin does not do;
- **misstate the source text**: a Chinese reading, a line marker, a hexagram number or a translation attributed to a source that does not say it;
- **commit personal data**: a real name (the owner's included), an email address, a reading's questioner or question, a token. The repository's own addresses are allowed;
- **break a reference a script cannot see**: a link in prose to a file, section or URL that does not exist, or an instruction that names a script, flag or setting the repository does not have;
- **weaken a check**: a test removed or loosened, a check skipped, a CI step made optional, without the PR saying why;
- **change the skill's stance or design** (what a reading is, what it leaves out) without the PR body naming where the owner approved it;
- **break a Claude Directory requirement no script checks**: the rows the rule `claude-directory` marks Human or Gap.

Everything else is Nit at most: wording, structure, style, naming.

## Verification bar

Before posting an Important finding, cite `file:line` in the changed files and say what an agent would do there. A claim about how a tool or service behaves needs its source (a doc URL, a line of code), not an inference from a name. If you cannot reach the source, say so and post it as a question, not a finding.

## Cap the nits

Post at most five Nits per review. Mention the rest as a count in the summary. If everything you found is a Nit, open the summary with "No blocking issues".

## After the first review

On later pushes to the same PR, post new Important findings only, and say which earlier findings the push resolved.

## Do not report

- Anything a workflow under `.github/workflows/` enforces; each workflow's header says what it catches.

## Releases

A release is a tag on `main` pushed to the release repository: whatever it contains reaches every install. In addition to the above, report as Important when missing:

- for each skill whose `SKILL.md`, a pattern or a reference file changed since `main`, the PR body shows verification level 2 (blind review) or higher, and says what it could not see (the rule `branches-and-releases`);
- the README's install instructions still match the repository's layout.
