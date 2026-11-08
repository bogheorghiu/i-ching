# i-ching-reading

Development repository for the `i-ching-reading` Agent Skill: I Ching readings that start from the hexagram's structure and the Chinese text. The skill and what it does are in [`plugins/i-ching-reading/`](plugins/i-ching-reading/); start with its [`SKILL.md`](plugins/i-ching-reading/skills/i-ching-reading/SKILL.md).

It is written to the open [Agent Skills](https://agentskills.io/specification) format, and the plugin folder is also an [Agent Plugin](https://agent-plugins.org) and a Claude plugin. Installs are meant to come from the release repository in the `vasana-works` organisation, once there is one; nothing is released yet. This repository is public.

## Provenance

The skill was developed in a private repository, `bogheorghiu/personal-use-tools` (folder `i-ching-reading/`), and moved here at its commit `b019028` (version 0.2.2, after a claims audit). This repository starts with fresh history instead of carrying that one; the audit's record stays on that repository's branch `archive/i-ching-audit-2026-11-02`.

## Working here

[`AGENTS.md`](AGENTS.md) holds the rules for any person or agent changing this repository. Tests: `for t in tests/test_*.py; do python3 "$t"; done`; the rest of CI is in [`.github/workflows/`](.github/workflows/).

## Licence

MIT ([`LICENSE`](LICENSE)), chosen by the owner on 2026-11-04. The skill folder carries its own copy, so an install that takes only the skill keeps it. The licence covers what was written here; whether the bundled Chinese text and the English name sets may be redistributed are open questions in this repository's issues.
