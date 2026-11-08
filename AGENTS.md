# Agent instructions

For every agent working in this repo, whatever its harness (Claude Code reads this through
`CLAUDE.md`; Codex, Cursor, Gemini and others read `AGENTS.md` directly). This file is
owner-gated: change it by PR, and the owner reviews that PR.

The repo runs **semi-autonomously**: agents branch, open PRs and merge their own PRs, except
PRs that touch a path `.github/CODEOWNERS` gives an owner. Those wait for the owner's review.
The whole security model is one fact: a merge to `main` needs the owner exactly when it
touches an owned path. So what is owned decides what an agent can change alone.

## 1. Is this the template, or a repo made from it?

Read the repo name (`git remote get-url origin`).

- **`bogheorghiu/semi-autonomous` (the template).** Changes here reach every future repo made
  from it, and none that already exist (GitHub copies files once, at creation). Keep it
  generic: no project-specific paths, keys, or names.
- **Any other repo.** It was made from the template (or copied from one). Its first session
  runs section 2 before any other work, and records what it found in its PR description.

## 2. First session in a new repo

GitHub's docs say a repo made from a template gets the template's files and directory structure.
They do not mention settings, rulesets, secrets or collaborators (read 2026-11-03, docs page
"Creating a repository from a template"). So treat all of these as absent until read back.

1. **Read the ruleset on `main`:** `GET /repos/{owner}/{repo}/rules/branches/main`. Without a
   rule requiring pull requests *and* code-owner review, CODEOWNERS gates nothing and every
   PR is mergeable by anyone with push. Report what you read; do not assume.
2. **Read `GET /repos/{owner}/{repo}/codeowners/errors`.** It must be empty.
3. **Propose, in one PR (owner-gated):** the project-specific CODEOWNERS lines (section 3),
   the plugins this project needs (section 6), and removal of any template line whose file
   type this project will never have only if the owner asks (spare lines cost nothing).
4. **Hand the owner the checklist below** as a comment on that PR or on the project's board.
   You cannot do these yourself, and should not be able to: an agent that can change rulesets
   can remove its own gate.

### Owner checklist (one-time, settings an agent cannot reach)

- Ruleset on `main`: require a pull request; required approvals 0; **require review from
  Code Owners**; dismiss stale approvals on push; block force pushes and deletion; required
  status checks `codeowners-guard`, `secrets` and `parity` (and the project's tests once they
  exist), each with its source set to GitHub Actions, so no other app or token can post a
  check of the same name; the agent account is never on the bypass list. Code owners and
  rulesets on a private repo need GitHub Pro or higher.
- Settings → General: allow auto-merge; squash merging only; delete head branches on merge.
- Settings → Actions: workflow permissions read-only; "allow GitHub Actions to create and
  approve pull requests" off; allowed actions limited to GitHub-owned and verified creators;
  Actions spending limit as low as the project allows.
- **No Actions secret this repo can see, ever** (repository- or organization-level). Any
  workflow an agent pushes on a branch runs with them before review (section 5). A secret a
  workflow truly needs goes in an environment whose deployment branches are `main` only; the
  job that names that environment runs only owned code (it runs merged code, and unowned code
  merges without you).
- PII: create the environment `pii-denylist` (deployment branches: `main` only) and set
  `PII_DENYLIST` there (one term per line), or run `.githooks/overwrite-ci-denylist`, which
  writes it there. A new repo has no environments: until then the PII jobs warn and pass.
- Never open a session (Claude Code or any agent) on an agent's branch, and never install or
  `direnv allow` there: its hooks and MCP servers would run with your credentials. Review in
  the GitHub UI or from the diff.
- The agent account: write access, never admin or maintain, and a different GitHub identity
  from the code owner (an owner reviewing their own account's PR is no review).
- Agent environments (cloud environment setup script, devcontainer, local clone): run
  `git config core.hooksPath .githooks` before the first commit, or the PII hooks never fire.
- Prove the gate once: an agent PR that touches only `.gitignore` must show "Review required"
  and be unmergeable by the agent; a PR touching only `README.md` must merge without review;
  `codeowners-guard`, `secrets` and `parity` must each have run green once before they are
  made required (a required check that never reports blocks every merge).
- Check that the agent account has no write access to the plugin marketplaces this repo
  enables (`bogheorghiu/shared-rules`, `bogheorghiu/prompt-design`), or that those repos carry
  the same gate: their code runs unread in every local session here.

Where these come from, with the council record that argued them: `bogheorghiu/negative-spiral`,
`docs/security-model.md`. That repo is the looser reference (most PRs auto-merge);
`bogheorghiu/board-pattern` is the tighter one (it also owns every script its hooks and
scheduled tasks run).

## 3. When a path gets an owner

A path is owned when a change to it, merged without a human reading it, could:

1. **run code that holds a secret or the agent's credentials** (CI workflows, dependency
   manifests and lockfiles, package-manager config, install hooks);
2. **change what agents load, run or may do** (`.claude/`, `.mcp.json`, `CLAUDE.md`,
   `AGENTS.md`, other harnesses' config, git hooks, devcontainers, editor tasks);
3. **change the gate** (`.github/`, which holds CODEOWNERS, the workflows and the guard);
4. **let a later, ungated change do 1-3.** The common case: an owned file *runs* an unowned
   one. A hook in `.claude/settings.json` that calls `scripts/check.sh` runs whatever the
   next ungated PR writes into `check.sh`. So the script is owned too;
5. **leak what must stay out of history** (`.gitignore`, which keeps key files and the PII
   denylist out of `git add -A`).

Everything else stays free: source code, tests, docs, prompts, examples. Overhead is the
cost of this design; a path is owned only when one of the five reasons applies. Each line in
CODEOWNERS carries its reason in a comment.

Project-specific lines a new repo usually needs:

- the file that reads an API key and decides where to send it (one file, so the rest of
  `src/` stays free; move key handling into it first if it is spread out);
- config files a documented command loads and that can redirect a key (e.g. a `baseUrl`
  in an example config the README tells agents to run);
- any script, module or data file an owned file runs or imports.

When you add a new kind of file that an agent harness, git, an editor or a package manager
loads by itself, and it is not in CODEOWNERS: add the line, in its own PR.

## 4. The tripwire: `codeowners-guard`

`.github/scripts/codeowners_guard.py` runs in CI on every PR. It fails when:

- a tracked file matching its list of run-or-load-unread names (agent config for the
  harnesses above, git hooks, devcontainers, manifests, lockfiles, `.gitignore`) is not owned;
- an owned file that runs things (hooks in `.claude/settings*.json`, workflows, git hooks,
  `.mcp.json`, `package.json`, devcontainer, editor tasks, pre-commit config) names a tracked
  file that is not owned, followed transitively, with Python sibling imports;
- CODEOWNERS, the guard or its workflow are not covered;
- GitHub reports a CODEOWNERS line it could not parse.

When it is red: add the missing CODEOWNERS line **in a separate PR**, so your other changes
can still merge alone. Never edit the guard, its lists or its workflow to make it pass. Those
live under `/.github/`, so that PR goes to the owner anyway, and now looks like an evasion.

What a green run does not prove: a harness that loads a file name not on the guard's list is
not seen; a path assembled at run time is not seen; imports in languages other than Python
are not followed. Run it locally before pushing: `python3 -I .github/scripts/codeowners_guard.py`.

## 5. PII gate

`.githooks/` and `.github/workflows/pii-denylist-guard.yml` come from the `pii-gate` of
`bogheorghiu/ex-cog-dev` (`security-toolkit`). They block personal names from reaching the
remote and run gitleaks for secrets. All of it is owner-gated, and it works for any agent,
since it is git and CI, not a plugin.

- Per clone: `git config core.hooksPath .githooks`, then put one term per line in
  `pii-denylist.local` (gitignored, never committed). With no denylist the hooks block every
  commit; they fail closed on purpose.
- Remote check: the workflow's `denylist` and `history` jobs read `PII_DENYLIST`, which lives
  **only** as a secret of the environment `pii-denylist`, whose deployment branches are the
  default branch only. Never as a repository- or organization-level secret: GitHub gives a
  same-repo branch's workflow run those, so an agent that pushes a branch with an edited
  workflow could print the denylist (the very names it protects) into a run log before any
  review. The workflow names the environment only on default-branch runs, so branch runs
  warn "NOT checked" by design and stay green; a branch workflow that names the environment
  itself is refused by the deployment-branch rule. If a branch run can read the secret, the
  job says so: move it into the environment. Environment secrets on a private repo need
  GitHub Pro, Team or Enterprise; on Free, leave the secret unset.
- What that buys: before merge, the local hooks are the only name scan, and an agent can skip
  them with `--no-verify` or by never arming them (they catch carelessness, not intent). After
  merge, the default-branch run scans the tree and every branch's history: it detects a name
  that got in, it does not prevent it.
- `secrets` (gitleaks over every commit) needs no secret and should be a required check. It
  ignores inline `gitleaks:allow` comments and runs with its own config from outside the
  checkout, so no repo file can loosen it. It reports after the push: a key it finds is
  already on the remote, in `refs/pull/*` too, and must be rotated, not just deleted.
- Prove it once: add a throwaway term, commit a file containing it, and watch the hook block.

## 6. Plugins

`.claude/settings.json` enables plugins for Claude Code sessions run **locally** (CLI, desktop,
IDE) in this repo, once the folder is trusted. **Cloud sessions do not install them**: per the
Claude Code docs ("Configure cloud environments", read 2026-11-03), a cloud session does not
install plugins a repo enables under `enabledPlugins`, nor plugins from marketplaces it lists.
Cloud sessions get plugins from the owner's claude.ai account instead. Repo hooks, `.mcp.json`
servers, `.claude/skills/`, `.claude/rules/` and `CLAUDE.md` do load in cloud sessions, which
is why `.claude/` and `.mcp.json` are owned.

Each enabled plugin loads hooks, skills and MCP servers unread, at whatever version its
marketplace serves today. CODEOWNERS gates *enabling* a plugin, not later updates to its code;
those are gated, if at all, in the marketplace's own repo. So at project scope:

- only plugins this repo's process depends on, from sources the owner controls or trusts;
- personal workflow plugins (code review, skill authoring, writing style) go in the user's or
  the cloud environment's own settings instead;
- no rule or safeguard that lives only in a plugin: cloud sessions and non-Claude agents never
  load it, so it belongs in this file, CODEOWNERS or CI;
- no plugin that persists memory across sessions (instructions planted there outlive the PR
  gate, and nothing in git shows them), and no plugin that pulls untrusted web content into
  sessions that act unattended, unless the project needs it and the owner says so.

To propose a plugin: a PR to `.claude/settings.json` stating what the project needs it for.

## 7. Working here

- One branch per session, one PR per change. Write the PR's merge criterion before any review.
- A branch you did not write is untrusted until merged: its `.claude/` hooks, `.mcp.json`,
  `.envrc` and install scripts run if you open a session in it or install from it. Review
  another agent's PR from its diff, not from a checkout of it; never run `direnv allow` or a
  package install on a branch you did not write.
- Before merging your own PR: a blind review (a fresh agent given the diff and a checkout of
  `main`, never of the PR branch, asked an open question, given no web content), every
  blocking finding fixed, checks green, `main` merged in.
- A PR that touches an owned path: open it ready for review (a draft requests no code owner),
  keep owned files in their own PR when you can, and push nothing after the owner approves
  (a push dismisses the approval).
- Never: a secret in the tree; a workflow action not pinned to a full commit SHA; a dependency
  change without its lockfile; a hook, MCP server or permission outside an owner-gated PR.
- Coordination across sessions, if the project needs it: `bogheorghiu/board-pattern`.
  This repo has a board: see `BOARD.md`.

## 8. This project: the `i-ching-reading` skill

Sections 1-7 are the template's and govern security and merging. This section is this
project's own, from `bogheorghiu/afk-ease`, whose packaging this repository reuses.

- **State the why.** Every decision, rule and instruction written here carries its reason, so
  the next reader can apply it to a case its author never saw. Where a rule must hold exactly
  and a script can enforce it, it goes in the script.
- **What ships.** `plugins/<plugin>/` is what an install receives: a plugin in two formats at
  once (the rule `agent-plugins-first`), its skills at `skills/<name>/SKILL.md` plus the files
  each references. Nothing outside `plugins/` ships; `tests/` checks the skill against its
  bundled text, `docs/` holds proposals that do not ship. The tree is the inventory (the rule
  `filesystem-is-the-index`).
- **Rules** live in `.claude/rules/`, one file each, each with its reason, named by file. A rule
  with `paths:` applies to changes of matching files; one without applies to every change.
  Claude Code loads them by that frontmatter; OpenCode loads all of them through
  `opencode.json`; every other agent reads the matching ones by hand before changing a file
  (whether they do is untested).
- **Branches and releases:** the rule `branches-and-releases`.
