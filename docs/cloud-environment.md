# Cloud environment for sessions on this repository (proposal)

**Status: a proposal, 2026-11-04.** Generic on purpose: nothing below is specific to this project except the two API hosts, so it can move into the `semi-autonomous` template as is. The environment itself is configured in claude.ai (the cloud environment menu in a session's title bar, then Edit); this file is the copy to paste from and to review changes against.

## Setup script

The template's owner checklist says agent environments must arm the PII hooks before the first commit (`AGENTS.md`, "Owner checklist"). The setup script cannot read the environment's secrets (Claude Code environment docs, read 2026-11-04), so it holds no key.

```bash
#!/usr/bin/env bash
# Arm the template's git hooks in every repository cloned into the session.
# Whether the script runs before or after the clone is UNRESOLVED; set it globally so
# both orders work: every repo with a .githooks/ folder uses it.
set -euo pipefail
git config --global core.hooksPath .githooks
# The denylist the hooks read. Without terms they block every commit (fail closed).
# The terms are personal, so they are not in this script: put them in the environment
# variable PII_DENYLIST (one term per line, or separated by |), which the hooks read.
```

A global `core.hooksPath` of `.githooks` also applies to repositories without that folder; git then finds no hooks there, which is the same as having none.

## Environment variables and credentials

| Name | What | Where |
|---|---|---|
| `PII_DENYLIST` | the personal terms the hooks block | environment variable |
| `OPENROUTER_API_KEY` | OpenRouter (and Claude through OpenRouter BYOK) | environment secret, or the proxy-injected credential for `openrouter.ai` |
| `DEEPSEEK_API_KEY` | DeepSeek chat and tool API | environment secret, or the proxy-injected credential for `api.deepseek.com` |

Never an Actions secret (`AGENTS.md`, owner checklist). With proxy-injected credentials, scripts send any placeholder and the proxy substitutes the key; `research/keys.py` works either way.

## Network

Allow at least: `github.com` (through the session's git proxy), `openrouter.ai`, `api.deepseek.com` (paths `/anthropic`, `/v1/tools/search`, `/v1/tools/fetch`), `pypi.org` and `registry.npmjs.org` only if a task installs packages. Hosts that ask automated readers not to scrape them (ctext.org) stay off the list on purpose.
