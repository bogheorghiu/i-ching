# Agent Plugins first, Claude equally

(No `paths:` frontmatter on purpose: a change to what ships can pass in one format while
breaking the other, so this loads every session.)

**Why.** What ships from here should run in any agent. Agent Skills (agentskills.io) and
Agent Plugins 1.0.0 (agent-plugins.org) are the open formats for that; Claude's plugin
system, its marketplace and its Directory are one client, with features the standard leaves
out. The owner's order: design for the standard first, then, equally, for Claude; where the
two diverge, give both the same function as far as each format allows. What the Claude
Directory itself requires is the rule `claude-directory`.

**One manifest is edited by hand: `plugins/<plugin>/plugin.json`** (Agent Plugins). Claude's
`.claude-plugin/plugin.json` and each bundled skill's `metadata.version` are written from it
by `.github/scripts/sync_manifests.py`; its docstring says what it derives and how to run it,
`--bump` included. A hand edit to a derived file cannot land: CI (`skills-ci.yml`) and the
pre-commit hook run `sync_manifests.py --check`, and in Claude Code the PostToolUse hook in
`.claude/settings.json` rewrites the derived files after every edit. `check_skills.py` checks
the root manifest's shape (the pinned `$schema`, only the spec's fields), and
`plugin-validate.yml` runs Claude's own validator over the other. The copy is generated, not
symlinked, because the Directory blocks a symlink the plugin loads, git on Windows checks a
symlink out as a text file by default, and Codex refuses a symlinked root manifest.

**MCP servers** go in `mcp.json` (Agent Plugins) and `.mcp.json` (Claude), two regular files
naming the same servers; `check_skills.py` fails on one file without the other, or on
different server names. No plugin here declares a server yet, so nothing derives one file
from the other.

**Components the standard does not package** (hooks, commands, agents, `userConfig`) are not
Claude-only for that reason: most coding agents have hooks, each with its own file and event
names. Write the logic once, as a script, and declare it per agent (Claude's
`hooks/hooks.json`; for Agent Plugins, a reverse-domain folder named in `extensions`). Where
an agent lacks the feature, give it the same function by another route if one exists, and
say in the PR where none does.

**A skill's frontmatter holds only the Agent Skills spec's keys** (`check_skills.py`
enforces it). An agent-specific setting goes under `metadata` or in a file that agent reads,
and no skill depends on one for correct or safe behaviour, because the other agents ignore
it.

**Each skill folder stands alone**, whatever else the plugin holds: the rule
`skill-md-stays-self-contained`.

**Sources.** agent-plugins.org/specification (components, `extensions`, the closed field
set) and agentskills.io/specification (frontmatter keys), read 2026-09-28. On symlinks, read
2026-09-29: claude.com/docs/plugins/pre-submission-checklist; git's `core.symlinks`
documentation; openai/codex `codex-rs/utils/plugins/src/plugin_namespace.rs`.
