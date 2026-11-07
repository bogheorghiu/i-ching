#!/usr/bin/env python3
"""Tests for check_skills.py. Run: python3 .github/scripts/test_check_skills.py"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOOD = """---
name: {name}
description: Does a thing. Use when a thing is needed.
license: MIT
metadata:
  version: "1.0"
---
See `patterns/a.md` and the overlay's `CHANGELOG.md`.
"""


def run(skill_md, dirname="demo", extra=None):
    with tempfile.TemporaryDirectory() as t:
        d = Path(t, "skills", dirname)
        (d / "patterns").mkdir(parents=True)
        (d / "patterns" / "a.md").write_text("x")
        (d / "SKILL.md").write_text(skill_md)
        for rel, body in (extra or {}).items():
            (d / rel).write_text(body)
        p = subprocess.run([sys.executable, str(HERE / "check_skills.py"), t], capture_output=True, text=True)
        return p.returncode, p.stderr


CASES = [
    ("valid skill passes; bare overlay filename is not a skill reference", GOOD.format(name="demo"), "demo", None, 0, ""),
    ("name must match directory", GOOD.format(name="other"), "demo", None, 1, "does not match directory"),
    ("uppercase name rejected", GOOD.format(name="Demo"), "Demo", None, 1, "naming rule"),
    ("double hyphen rejected", GOOD.format(name="de--mo"), "de--mo", None, 1, "naming rule"),
    ("unquoted numeric metadata rejected", GOOD.format(name="demo").replace('"1.0"', "1.0"), "demo", None, 1, "not load as a string"),
    ("unquoted date metadata rejected", GOOD.format(name="demo").replace('version: "1.0"', "released: 2026-09-25"), "demo", None, 1, "not load as a string"),
    ("unquoted yes/no metadata rejected", GOOD.format(name="demo").replace('version: "1.0"', "beta: yes"), "demo", None, 1, "not load as a string"),
    ("semver-looking metadata is a string and passes", GOOD.format(name="demo").replace('"1.0"', "1.2.3"), "demo", None, 0, ""),
    ("folded description passes", GOOD.format(name="demo").replace("description: Does a thing. Use when a thing is needed.", "description: >-\n  Does a thing.\n  Use when needed."), "demo", None, 0, ""),
    ("trailing comment on name passes", GOOD.format(name="demo").replace("name: demo", "name: demo # the id"), "demo", None, 0, ""),
    ("agent-specific frontmatter key rejected", GOOD.format(name="demo").replace("license: MIT", "license: MIT\ndisable-model-invocation: true"), "demo", None, 1, "outside the Agent Skills spec"),
    ("every spec key together passes", GOOD.format(name="demo").replace("license: MIT", "license: MIT\ncompatibility: Needs network access\nallowed-tools: Read"), "demo", None, 0, ""),
    ("a URL in SKILL.md is rejected", GOOD.format(name="demo") + "More at https://example.org/x.\n", "demo", None, 1, "links outside the skill"),
    ("a URL in a reference file passes", GOOD.format(name="demo"), "demo", {"patterns/b.md": "Source: https://example.org/x (read 2026-09-29)"}, 0, ""),
    ("allowed-tools as block list rejected", GOOD.format(name="demo").replace("license: MIT", "license: MIT\nallowed-tools:\n  - Read"), "demo", None, 1, "allowed-tools"),
    ("dangling plain-text reference rejected", GOOD.format(name="demo"), "demo", {"patterns/b.md": "see patterns/gone.md step 2"}, 1, "does not resolve"),
    ("empty license rejected", GOOD.format(name="demo").replace("license: MIT", "license:"), "demo", None, 1, "license"),
    ("empty metadata value rejected", GOOD.format(name="demo").replace('version: "1.0"', "version:  "), "demo", None, 1, "not load as a string"),
    ("hex metadata rejected", GOOD.format(name="demo").replace('version: "1.0"', "build: 0x1F"), "demo", None, 1, "not load as a string"),
    ("quoted name with a comment passes", GOOD.format(name="demo").replace("name: demo", 'name: "demo" # id'), "demo", None, 0, ""),
    ("plain multi-line description passes", GOOD.format(name="demo").replace("description: Does a thing. Use when a thing is needed.", "description: Does a thing.\n  Use when needed."), "demo", None, 0, ""),
    ("a longer extension is not cut to a listed one", GOOD.format(name="demo"), "demo", {"patterns/b.md": "see assets/app.jsx"}, 0, ""),
    ("dangling ./ reference rejected", GOOD.format(name="demo"), "demo", {"patterns/b.md": "see ./patterns/gone.md"}, 1, "does not resolve"),
    ("a mis-indented metadata block is rejected, not folded into license", GOOD.format(name="demo").replace('metadata:\n  version: "1.0"', '  version: "1.0"'), "demo", None, 1, "missing parent key"),
    ("an escaped quote does not cut the description short", GOOD.format(name="demo").replace("description: Does a thing. Use when a thing is needed.", "description: 'Don''t " + "x" * 1100 + "'"), "demo", None, 1, "max 1024"),
    ("1e3 metadata rejected", GOOD.format(name="demo").replace('version: "1.0"', "build: 1e3"), "demo", None, 1, "not load as a string"),
    ("reference outside the skill rejected", GOOD.format(name="demo"), "demo", {"patterns/b.md": "see `../patterns/a.md`"}, 1, "outside the skill"),
    ("dangling reference rejected", GOOD.format(name="demo").replace("patterns/a.md", "patterns/missing.md"), "demo", None, 1, "does not resolve"),
    ("dangling reference in a pattern file rejected", GOOD.format(name="demo"), "demo", {"patterns/b.md": "see `sources/x.md`"}, 1, "does not resolve"),
    ("missing description rejected", GOOD.format(name="demo").replace("description: Does a thing. Use when a thing is needed.\n", ""), "demo", None, 1, "description"),
    ("over-long description rejected", GOOD.format(name="demo").replace("Does a thing.", "x" * 1100), "demo", None, 1, "max 1024"),
    ("install metadata rejected", GOOD.format(name="demo").replace('version: "1.0"', 'version: "1.0"\n  github-repo: x/y'), "demo", None, 1, "install metadata"),
    ("allowed-tools as list rejected", GOOD.format(name="demo").replace("license: MIT", "license: MIT\nallowed-tools: [Read]"), "demo", None, 1, "allowed-tools"),
]

import json

README = "# Demo\n\n" + " ".join(["word"] * 45) + "\n"
MANIFEST = {"name": "demo", "version": "1.0.0", "license": "MIT", "description": "Demo."}
MARKET = {"name": "m", "owner": {"name": "o"}, "plugins": [{"name": "demo", "source": "./plugins/demo"}]}


SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"


def run_plugin(manifest=MANIFEST, readme=README, market=MARKET, skill_version='"1.0"', extra_dirs=(),
               agent_manifest="same", plugin_files=None):
    """Build plugins/demo/ (manifest, README, skills/demo/SKILL.md) plus a marketplace, lint it."""
    with tempfile.TemporaryDirectory() as t:
        d = Path(t, "plugins", "demo")
        sk = d / "skills" / "demo"
        (sk / "patterns").mkdir(parents=True)
        (sk / "patterns" / "a.md").write_text("x")
        (sk / "SKILL.md").write_text(GOOD.format(name="demo").replace('"1.0"', skill_version))
        if manifest is not None:
            (d / ".claude-plugin").mkdir()
            (d / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest))
        if agent_manifest is not None:
            am = agent_manifest if agent_manifest != "same" else {"$schema": SCHEMA, **(manifest or {})}
            (d / "plugin.json").write_text(json.dumps(am))
        for rel, body in (plugin_files or {}).items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(body)
        if readme is not None:
            (d / "README.md").write_text(readme)
        for sub in extra_dirs:
            (d / sub).mkdir()
        if market is not None:
            Path(t, ".claude-plugin").mkdir()
            Path(t, ".claude-plugin", "marketplace.json").write_text(json.dumps(market))
        p = subprocess.run([sys.executable, str(HERE / "check_skills.py"), t], capture_output=True, text=True)
        return p.returncode, p.stderr


PLUGIN_CASES = [
    ("valid plugin passes; 1.0 matches 1.0.0", {}, 0, ""),
    ("missing plugin.json rejected", {"manifest": None}, 1, "missing .claude-plugin/plugin.json"),
    ("plugin name must match folder", {"manifest": {**MANIFEST, "name": "other"}}, 1, "does not match folder"),
    ("non-semver version rejected", {"manifest": {**MANIFEST, "version": "1.0"}}, 1, "is not x.y.z"),
    ("missing licence rejected", {"manifest": {k: v for k, v in MANIFEST.items() if k != "license"}}, 1, "no licence"),
    ("missing README rejected", {"readme": None}, 1, "missing README.md"),
    ("short README rejected; code blocks do not count", {"readme": "# Demo\n\nshort\n```\n" + "w " * 60 + "\n```\n"}, 1, "fewer than 40 words"),
    ("top-level bin/ rejected", {"extra_dirs": ("bin",)}, 1, "bin/"),
    ("skill version out of step with plugin rejected", {"skill_version": '"1.1"'}, 1, "does not match demo metadata.version"),
    ("missing Agent Plugins root manifest rejected", {"agent_manifest": None}, 1, "missing root plugin.json"),
    ("wrong $schema rejected", {"agent_manifest": {"$schema": "x", **MANIFEST}}, 1, "$schema must be"),
    ("a field Agent Plugins rejects is caught", {"agent_manifest": {"$schema": SCHEMA, **MANIFEST, "displayName": "D"}}, 1, "rejects: ['displayName']"),
    ("manifests that disagree are rejected", {"agent_manifest": {"$schema": SCHEMA, **MANIFEST, "version": "1.0.1"}}, 1, "version differs"),
    ("a development AGENTS.md inside the plugin is rejected", {"plugin_files": {"AGENTS.md": "x"}}, 1, "development file AGENTS.md"),
    ("a nested .claude folder inside the plugin is rejected", {"plugin_files": {"skills/demo/.claude/x.md": "x"}}, 1, "development file .claude"),
    ("mcp.json without .mcp.json rejected", {"plugin_files": {"mcp.json": '{"mcpServers": {"a": {}}}'}}, 1, "must both exist"),
    ("mcp.json and .mcp.json with different servers rejected", {"plugin_files": {"mcp.json": '{"mcpServers": {"a": {}}}', ".mcp.json": '{"mcpServers": {"b": {}}}'}}, 1, "different servers"),
    ("matching mcp.json and .mcp.json pass", {"plugin_files": {"mcp.json": '{"mcpServers": {"a": {}}}', ".mcp.json": '{"mcpServers": {"a": {"x": 1}}}'}}, 0, ""),
    ("short skill version with a pre-release suffix matches the full form", {"manifest": {**MANIFEST, "version": "1.0.0-beta"}, "skill_version": '"1.0-beta"'}, 0, ""),
    ("unlisted plugin rejected", {"market": {**MARKET, "plugins": []}}, 1, "not listed in marketplace.json"),
    ("marketplace source without a manifest rejected", {"market": {**MARKET, "plugins": [{"name": "demo", "source": "./plugins/nothing"}]}}, 1, "has no .claude-plugin/plugin.json"),
]

fails = 0
for label, md, dirname, extra, want_rc, want_err in CASES:
    rc, err = run(md, dirname, extra)
    ok = rc == want_rc and want_err in err
    fails += not ok
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  (rc={rc}, stderr={err.strip()!r})"))
for label, kwargs, want_rc, want_err in PLUGIN_CASES:
    rc, err = run_plugin(**kwargs)
    ok = rc == want_rc and want_err in err
    fails += not ok
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  (rc={rc}, stderr={err.strip()!r})"))
total = len(CASES) + len(PLUGIN_CASES)
print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
