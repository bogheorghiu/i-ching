# i-ching-reading

An Agent Skill for I Ching (Book of Changes) readings: casting a hexagram, or taking one the user already cast, and reading its structure from the bundled Chinese text. What it does and how is in [`skills/i-ching-reading/SKILL.md`](skills/i-ching-reading/SKILL.md).

## What it runs, sends and fetches

- It runs one local Python script, `skills/i-ching-reading/scripts/yarrow_simulation.py`, which casts a hexagram by simulated yarrow stalks or coins with Python's standard library only. It reads no files outside the skill folder and writes none.
- It sends nothing anywhere and fetches nothing from the network. The Chinese text it reads from is bundled in `skills/i-ching-reading/references/`.

## Licence

See [`skills/i-ching-reading/LICENSE`](skills/i-ching-reading/LICENSE).
