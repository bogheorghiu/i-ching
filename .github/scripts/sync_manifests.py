#!/usr/bin/env python3
"""Write every plugin file derived from plugins/<plugin>/plugin.json, or check that they match.

plugins/<plugin>/plugin.json (the Agent Plugins manifest) is the only manifest edited by
hand. From it this script derives:
  - .claude-plugin/plugin.json: the same fields without $schema and extensions, plus
    displayName (the name, title-cased), which Claude shows and Agent Plugins rejects;
  - metadata.version in each bundled skill's SKILL.md, because Claude Code updates an
    installed plugin only when its version changes and skill-only installs read the skill's.

Usage:
  python3 .github/scripts/sync_manifests.py                 write the derived files
  python3 .github/scripts/sync_manifests.py --check         exit 1 if any derived file is stale
  python3 .github/scripts/sync_manifests.py --bump patch|minor PLUGIN   raise the version, then write
"""
import json
import re
import sys
from pathlib import Path

VERSION_LINE = re.compile(r'^(\s+version:\s*)"?[^"\n]*"?\s*$', re.M)


def claude_manifest(source):
    out = {k: v for k, v in source.items() if k not in ("$schema", "extensions")}
    out = {"name": out["name"], "displayName": out["name"].replace("-", " ").title(),
           **{k: v for k, v in out.items() if k != "name"}}
    return json.dumps(out, indent=2) + "\n"


def with_skill_version(text, version):
    """Rewrite metadata.version inside the frontmatter only."""
    end = text.find("\n---", 4)
    head, rest = text[:end], text[end:]
    if "\nmetadata:" not in head:
        head += f'\nmetadata:\n  version: "{version}"'
    elif VERSION_LINE.search(head.split("\nmetadata:", 1)[1]):
        pre, meta = head.split("\nmetadata:", 1)
        head = pre + "\nmetadata:" + VERSION_LINE.sub(lambda m: f'{m.group(1)}"{version}"', meta, count=1)
    else:
        head = head.replace("\nmetadata:", f'\nmetadata:\n  version: "{version}"', 1)
    return head + rest


def derived_files(plugin_dir):
    """Map each derived path to the content it should have."""
    source = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
    files = {plugin_dir / ".claude-plugin" / "plugin.json": claude_manifest(source)}
    for skill_md in sorted(plugin_dir.glob("skills/*/SKILL.md")):
        files[skill_md] = with_skill_version(skill_md.read_text(encoding="utf-8"), source["version"])
    return files


def bump(plugin_dir, part):
    path = plugin_dir / "plugin.json"
    source = json.loads(path.read_text(encoding="utf-8"))
    major, minor, patch = (int(x) for x in source["version"].split("-")[0].split("."))
    source["version"] = f"{major}.{minor + 1}.0" if part == "minor" else f"{major}.{minor}.{patch + 1}"
    path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    print(f"{plugin_dir.name}: {source['version']}")


def main(argv):
    root = Path(__file__).resolve().parents[2]
    plugins = sorted(p.parent for p in (root / "plugins").glob("*/plugin.json"))
    if argv[:1] == ["--bump"]:
        if len(argv) != 3 or argv[1] not in ("patch", "minor") or not (root / "plugins" / argv[2] / "plugin.json").is_file():
            sys.exit("usage: sync_manifests.py --bump patch|minor PLUGIN")
        bump(root / "plugins" / argv[2], argv[1])
        argv = []
    check = argv == ["--check"]
    stale = []
    for plugin_dir in plugins:
        for path, want in derived_files(plugin_dir).items():
            have = path.read_text(encoding="utf-8") if path.is_file() else None
            if have == want:
                continue
            if check:
                stale.append(path.relative_to(root))
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(want, encoding="utf-8")
                print(f"wrote {path.relative_to(root)}")
    if stale:
        print("stale, derived from plugin.json: " + ", ".join(map(str, stale)), file=sys.stderr)
        print("fix: python3 .github/scripts/sync_manifests.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
