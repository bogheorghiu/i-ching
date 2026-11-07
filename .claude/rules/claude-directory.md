---
paths:
  - "plugins/**"
  - ".claude-plugin/marketplace.json"
---

# What the Claude Directory requires of a plugin folder

The Claude Directory (claude.ai/directory/manage) is one of the two targets everything here
ships to; the other is any agent that reads the open formats (the rule
`agent-plugins-first`). The Directory takes one plugin folder per submission, validates it
against its checklist, runs a security scan, and repeats both on every new commit of the
branch or tag it tracks. A version that fails cannot go live, and the listing keeps serving
the last one that passed. So a commit that breaks a requirement below does not break the
listing; it stops the next release from reaching it, and nothing here reports why. Releases
land on `main` (the rule `branches-and-releases`), so `main` is the branch to have it track.
Most checks read the plugin folder only; a few read the whole repository (`.gitattributes`,
archive size).

`claude plugin validate`, which `plugin-validate.yml` runs, checks that files are well-formed;
it does not check the Directory's requirements. The portal's own Validate does, and only on
the portal. The tables say which requirement a script here already catches, so a reviewer
spends their attention on the rest.

**Sources**, all read 2026-09-29: the checklist (claude.com/docs/plugins/pre-submission-checklist),
the build and submit pages (claude.com/docs/plugins/build, claude.com/docs/plugins/submit),
claude.com/docs/directory/publish, the CLI reference
(code.claude.com/docs/en/plugins/cli-reference), and the Directory Policy
(support.claude.com article 13145358, reached only through a summary, so its quotes are the
summary's). Results: **Blocks** (cannot submit until fixed), **Held** (an Anthropic reviewer
reads it before it goes live), **Warning**, and **Stops** (the portal cannot validate the
repository at all). **Human** means no script here decides it; **Gap** means a script
could, and none does.

## Layout and manifest

| Requirement | Result | Checked by |
|---|---|---|
| `.claude-plugin/plugin.json` in the folder (without it, listed for Claude Code only) | Blocks | `check_skills.py` |
| `name`: lowercase letters, digits and hyphens, up to 64, starting and ending with a letter or digit | Blocks for non-ASCII, else Warning | `check_skills.py` |
| `name` is not a reserved word as a whole (`claude`, `anthropic`, `official`, `plugin`, `mcp`, `test`), not made only of generic words, and presents nothing as official | Blocks / Held | Human (Gap for the reserved-word list) |
| `name`, `displayName` and `author.name` cannot be mistaken for another plugin, publisher, connector or brand; a fork takes a name of its own; no other organisation's plugin has the name | Held; Blocks for the same name | Human; the last only Anthropic's registry can see |
| `displayName` and `author.name` in one writing system, without look-alike letters or invisible characters | Blocks | `check_json_ascii.py` (JSON files are ASCII only) |
| Component keys (`hooks`, `mcpServers`, ...) spelled as the plugins reference does, and not inside `experimental` | Blocks | `plugin-validate.yml` (`--strict` fails on an unrecognised field) |
| `description`, `author` and `version` set; `version` raised with every release | Warning | `version`: `check_skills.py`; its rise: `version-bump-guard.yml`. `description`, `author`: Gap |
| README of 40 or more words outside code blocks, saying what the plugin does, how to use it, and everything it runs, sends or fetches | Blocks; the security scan reads the disclosure | Word count: `check_skills.py`. Content: human |
| `LICENSE` in the folder, or `license` in the manifest | Blocks | `check_skills.py` |
| No top-level `bin/` | claude.ai and Cowork cannot install it at all | `check_skills.py` |
| Skill, command and agent files: valid YAML frontmatter, `description` a single text value | Blocks | `SKILL.md`: `check_skills.py`. Commands and agents: none exist here |

## Files in the folder

| Requirement | Result | Checked by |
|---|---|---|
| Regular files only: no symbolic links, Git submodules or Git LFS pointers | Blocks where the plugin loads the entry, else Warning | `plugin-validate.yml` for a linked component folder or entry (`--strict`). Any other symlink: Gap |
| No `.DS_Store`, `Thumbs.db`, `desktop.ini` or `__MACOSX` entries | Blocks | Gap (`.gitignore` keeps out `.DS_Store` only) |
| Names valid on Windows and macOS: no colon, trailing dot or space, Windows device name, or two names differing only in case; folders on the plugin's path use letters, digits, dots, hyphens and underscores | Stops | Gap |
| No `export-ignore`, `export-subst`, `filter` (LFS included) or other content-rewriting attribute in any `.gitattributes`, the repository root included | Stops | Gap (no `.gitattributes` exists) |
| Size: repository under 50 MiB archived and 256 MiB unpacked, fewer than 10,000 entries; plugin at most 512 files; each file under 5 MiB, and under 256 KiB unless an image or font | Stops / Held | Gap |
| Only text files (SVG included), complete PNG, JPEG, GIF and WebP images, and fonts; readable source, not compiled, packed or minified | Held | Gap |
| No credential in any file, README examples included; a secret is asked for through `userConfig` with `sensitive: true` and used as `${user_config.KEY}`; no environment token sent to a server | Blocks / Held | gitleaks in `pii-denylist-guard.yml`, for known token shapes. The rest: human |
| A bundled image or font is shown from the README by Markdown image syntax only, never named in a command, hook, script, backticks or a code block | Held | Gap (none bundled yet) |

## If a plugin adds an MCP server or a hook (none does yet)

| Requirement | Result | Checked by |
|---|---|---|
| `.mcp.json` valid JSON with every server matching the schema; a remote server has `type` `http`, `sse` or `ws` and an absolute `https://` or `wss://` URL, `${user_config.KEY}` or `""`; a server is declared with `command` and `args` or `url`, never a `.mcpb` or `.dxt` bundle | Blocks (a local bundle: Held) | JSON validity: `check_skills.py`. Schema: Gap |
| A local server runs a file inside the plugin with plain arguments; every path in a hook or server command is written in full from `${CLAUDE_PLUGIN_ROOT}`, with no other variable, substitution, wildcard, shell, `-c` or `npm run`; the scripts they run contain no launcher or package install | Held; the path rule Blocks when the plugin is a subfolder, as here | Gap |
| A launcher package (`npx`, `uvx`, `bunx`, `pnpm dlx`, `yarn dlx`, `pipx run`, `uv run` with `--locked` or `--frozen`) is pinned to an exact version, and is Held even then; no `.npmrc`, `bunfig.toml` or `uv.toml`; no lockfile beside `package.json` in the plugin root | Blocks / Held | Gap |
| `hooks/hooks.json`: valid JSON, a top-level `hooks` object, only the hooks reference's events and types, `https://` on every HTTP hook | Blocks | Gap |

## Policy (all human)

- The description "must precisely match actual functionality", with "no unexpected
  functionality or promise undelivered features"; every instruction is human-readable, with
  nothing "hidden, obfuscated, or encoded".
- The plugin does not read Claude's memory, chat history, conversation summaries or the
  user's uploaded files, and does not call other external software unless the user asks.
- Prohibited categories include financial transactions or asset transfers, standalone
  image, video or audio generation (design tools excepted), and advertisement-focused
  software.

## Process

The repository is public before the listing goes live, and a paid plan submits. One
submission per repository and folder, at most 10 per organisation in 24 hours. The portal
asks data-handling questions (personal data, other services, retention, users under 18) and
four acknowledgements. A first submission that fails the security scan is rejected; a person
reviews a new listing before it goes live.
