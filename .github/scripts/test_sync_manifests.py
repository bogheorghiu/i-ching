#!/usr/bin/env python3
"""Tests for sync_manifests.py. Run: python3 .github/scripts/test_sync_manifests.py

Each case builds a throwaway repo with one plugin, because the script finds plugins from its
own location. The two drifts it closed were real: a field set in one manifest only
(homepage was not among the fields check_skills.py compared) and a hand edit to the Claude copy.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = {
    "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
    "name": "trip-scout",
    "version": "0.2.1",
    "description": "d",
    "license": "MIT",
}
SKILL = '---\nname: trip-scout\ndescription: d\nlicense: MIT\nmetadata:\n  version: "0.2.1"\n---\nbody version: 9\n'


def repo(source=SOURCE, skill=SKILL):
    t = Path(tempfile.mkdtemp())
    (t / ".github/scripts").mkdir(parents=True)
    shutil.copy(HERE / "sync_manifests.py", t / ".github/scripts/sync_manifests.py")
    p = t / "plugins/trip-scout"
    (p / "skills/trip-scout").mkdir(parents=True)
    (p / "plugin.json").write_text(json.dumps(source, indent=2) + "\n")
    (p / "skills/trip-scout/SKILL.md").write_text(skill)
    return t, p


def run(t, *args):
    return subprocess.run([sys.executable, str(t / ".github/scripts/sync_manifests.py"), *args],
                          capture_output=True, text=True).returncode


def claude(p):
    return json.loads((p / ".claude-plugin/plugin.json").read_text())


def case_write_then_check():
    t, p = repo()
    assert run(t, "--check") == 1, "missing Claude manifest must be stale"
    assert run(t) == 0 and run(t, "--check") == 0
    c = claude(p)
    assert "$schema" not in c and c["displayName"] == "Trip Scout" and c["version"] == "0.2.1"


def case_field_in_root_only_is_stale():
    t, p = repo()
    run(t)
    src = json.loads((p / "plugin.json").read_text())
    src["homepage"] = "https://example.org"
    (p / "plugin.json").write_text(json.dumps(src))
    assert run(t, "--check") == 1
    run(t)
    assert claude(p)["homepage"] == "https://example.org"


def case_hand_edit_of_claude_copy_is_stale():
    t, p = repo()
    run(t)
    c = claude(p)
    c["description"] = "edited by hand"
    (p / ".claude-plugin/plugin.json").write_text(json.dumps(c, indent=2) + "\n")
    assert run(t, "--check") == 1


def case_skill_version_follows_and_body_untouched():
    t, p = repo(skill=SKILL.replace('"0.2.1"', '"0.1"'))
    assert run(t, "--check") == 1
    run(t)
    text = (p / "skills/trip-scout/SKILL.md").read_text()
    assert 'version: "0.2.1"' in text and text.endswith("body version: 9\n")


def case_bump():
    t, p = repo()
    assert run(t, "--bump", "patch", "trip-scout") == 0
    assert claude(p)["version"] == "0.2.2" and '"0.2.2"' in (p / "skills/trip-scout/SKILL.md").read_text()
    run(t, "--bump", "minor", "trip-scout")
    assert json.loads((p / "plugin.json").read_text())["version"] == "0.3.0"
    assert run(t, "--bump", "major", "trip-scout") != 0 and run(t, "--bump", "patch", "nope") != 0


fails = 0
cases = [v for k, v in dict(globals()).items() if k.startswith("case_")]
for case in cases:
    try:
        case()
        print("PASS", case.__name__)
    except AssertionError as e:
        fails += 1
        print("FAIL", case.__name__, e)
print(f"{len(cases) - fails}/{len(cases)} passed")
sys.exit(1 if fails else 0)
