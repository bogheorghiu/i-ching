# Branches and releases: what each merge requires

(No `paths:` frontmatter on purpose: every change ends in a merge, so this loads every
session.)

This is the development repository. The public, installable copy is a separate release
repository in the `vasana-works` organisation (decided by the owner, 2026-11-03). Two
repositories, so work in progress never reaches an install, and the release repository is an
ordinary repository rather than a fork, so no fork network ties the public copy to this one.

**Into `main`** (every change, through a pull request from its own branch; never a direct
push). There is no `dev` branch: `main` is unreleased work here, because releases happen
elsewhere.

- CI green. Every pull request that changes the plugin raises its `version` in
  `plugins/i-ching-reading/plugin.json` (`sync_manifests.py --bump` does that and rewrites
  the derived files; the rule `agent-plugins-first`). Pre-1.0: patch for fixes, minor for
  anything that changes what the skill tells an agent to do; 1.0 is the owner's call.
- The PR body names what was verified: for a skill change, the level reached (the rule
  `verify-skill-changes`) and what it could not see; for a check or script, the mutations
  tried (the rule `verify-a-check-by-breaking-it`).
- Who merges: `AGENTS.md` (an agent merges its own PR unless it touches a path `.github/CODEOWNERS` owns). A version bump rewrites `plugins/*/.claude-plugin/plugin.json`, which is owned, so every PR that changes the plugin goes to the owner.

**A release** is a tag on `main` pushed to the release repository, so the published history
is this repository's history up to that tag. Before tagging:

1. Every skill file changed since the last release reached verification level 2 (blind
   review) at least once since then.
2. A reader that did not write the changes reviewed them against `REVIEW.md`.
3. Every issue labelled `release-blocker` is closed.
4. The owner says yes. Nothing becomes public (this repository's visibility, a release, a
   Directory submission) without it.

How the tag reaches the release repository (a workflow or a script) is not built yet (Gap;
tracked in an issue). Keep `main` the default branch of the release repository: install
commands and the marketplace read the default branch.

Open work is tracked in GitHub issues, not in files: a to-do list in a file goes stale while
still reading as current.
