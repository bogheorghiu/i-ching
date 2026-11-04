---
paths:
  - "plugins/*/skills/**"
---

# SKILL.md depends on nothing that can change outside the skill

Every run loads `SKILL.md`, and a skill is copied into agents we never see. Anything it
points at outside its own folder can move, change or disappear, and nothing in the skill
would notice. The rest of the plugin counts as outside: a skill-only install (through
`npx skills add` or `gh skill install`, or a copied folder) receives the skill folder
and nothing beside it.

- **No URL in `SKILL.md`** (`check_skills.py` enforces it). A source belongs in a
  reference or sources file, cited with the date it was read, where it can be re-checked
  and corrected without touching the core.
- **Optional extras** (a companion tool, an installable stack, another repository) are
  described in their own file inside the skill folder. Nothing else in the skill refers
  to that file, so deleting or rewriting it changes nothing about how the skill runs.
  Whether a skill may tell the user about such an extra, and how, is the owner's open
  decision; until it is made, the skill says nothing about it.
