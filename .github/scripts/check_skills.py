#!/usr/bin/env python3
"""Structural lint for every skill and plugin in the repository (stdlib only).

Skills live at plugins/<plugin>/skills/<skill>/SKILL.md (a bare skills/<skill>/ tree is
also accepted). Each plugin folder is what installs receive, and it is two things at once:
an Agent Plugin (agent-plugins.org 1.0.0: root plugin.json) and a Claude plugin
(.claude-plugin/plugin.json, which Claude and the Claude Directory read). So the plugin
checks cover the Directory's blocking rules a script can see (manifest name matches the
folder, x.y.z version, licence, README of 40+ words outside code blocks, no top-level
bin/, a marketplace entry), the Agent Plugins manifest's own rules, the two manifests
agreeing field by field, and no development-agent file inside the folder. The plugin
version must match each bundled skill's metadata.version, because Claude Code only
updates an installed plugin when that version changes.

Checks the Agent Skills spec (agentskills.io/specification) plus the extra
checks `gh skill publish` runs, so a PR fails here instead of at publish time:
name rules, description/compatibility length, metadata values as strings,
allowed-tools as a string, only the spec's keys, no URL in SKILL.md, no install metadata, license present, body <= 500
lines. Also checks that every backticked relative `*.md` path a skill file
mentions resolves inside that skill folder -- a dangling reference is a
silent failure for the agent that follows it.

Usage: python3 .github/scripts/check_skills.py [repo_root]   (exit 1 on any error)
"""
import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# `gh skill publish` treats metadata keys prefixed "github-" as install metadata
# written by `gh skill install` (cli/cli pkg/cmd/skills/publish, findGitHubMetadataKeys).
INSTALL_PREFIX = "github-"
# The Agent Skills spec's whole field set. Agent-specific extras (Claude's
# disable-model-invocation, say) would work in their own agent, but claude.ai rejects
# an upload whose frontmatter has any other key, and other agents ignore them, so a
# skill that relies on one silently loses that behaviour elsewhere.
# Every run loads SKILL.md, and a link there goes stale with nothing to notice it. A
# dated citation in a reference file can be re-checked and fixed without a core change.
URL_RE = re.compile(r"https?://[^\s)>`\]]+")
SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
# Folder-qualified file references, backticked or plain ("see patterns/lodging.md §5").
# A bare name such as CHANGELOG.md names a file in the user's overlay, not in the skill.
REF_RE = re.compile(r"(?<![\w/.-])((?:\.{1,2}/)*(?:patterns|reference|references|sources|scripts|assets)/[A-Za-z0-9_./-]*?[A-Za-z0-9_-]\.(?:md|py|js|json|txt))(?![A-Za-z0-9_])")
# Scalars YAML would load as something other than a string (bools incl. YAML 1.1's
# yes/no/on/off, null, numbers, dates); `gh skill publish` expects string values.
YAML_NON_STRING = re.compile(r"^(?:|~|null|true|false|yes|no|on|off|y|n|[-+]?[\d_]+|0x[\da-f_]+|0o[0-7_]+|0b[01_]+|[-+]?[\d_]+\.[\d_]*(?:e[-+]?\d+)?|[-+]?[\d_]*\.[\d_]+(?:e[-+]?\d+)?|[-+]?\d+e[-+]?\d+|[-+]?\.inf|\.nan|\d{4}-\d{2}-\d{2}.*)$", re.I)


def strip_comment(v):
    """Drop a trailing ' # comment', keeping a quoted scalar's quotes."""
    if v[:1] == "'":
        m = re.match(r"'(?:[^']|'')*'", v)          # '' is an escaped quote
        return m.group(0) if m else v
    if v[:1] == '"':
        m = re.match(r'"(?:[^"\\]|\\.)*"', v)      # backslash escapes
        return m.group(0) if m else v
    return re.split(r"\s+#", v, maxsplit=1)[0].rstrip()


def parse_frontmatter(text):
    """Parse the YAML subset skills use: scalars, block scalars (| and >), one nested
    map level (metadata), and block lists. Lists come back as Python lists."""
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with '---' frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError("frontmatter is not closed with '---'")
    lines, body = text[4:end].splitlines(), text[end + 4:].lstrip("\n")
    data, i = {}, 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw)
        if not m or raw[0] in " \t":
            raise ValueError(f"unparseable frontmatter line: {raw!r}")
        key, val = m.group(1), strip_comment(m.group(2))
        block = []
        while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
            block.append(lines[i])
            i += 1
        if val in ("|", "|-", "|+", ">", ">-", ">+"):
            parts = [b.strip() for b in block]
            data[key] = ("\n" if val[0] == "|" else " ").join(parts).strip()
        elif val == "" and block and block[0].strip().startswith("- "):
            data[key] = [strip_comment(b.strip()[2:]) for b in block if b.strip()]
        elif val == "":
            sub = {}
            for b in block:
                if not b.strip():
                    continue
                mm = re.match(r"^\s+([A-Za-z0-9_.-]+):\s*(.*)$", b)
                if not mm:
                    raise ValueError(f"unparseable nested line under {key}: {b!r}")
                sub[mm.group(1)] = strip_comment(mm.group(2))
            data[key] = sub
        else:
            # A plain scalar may continue on indented lines; YAML folds them with spaces. A
            # continuation that looks like a mapping or list item is a mis-indented block,
            # which YAML rejects, so the linter must too.
            cont = [b.strip() for b in block if b.strip()]
            bad = [c for c in cont if c.startswith("- ") or re.match(r"^[A-Za-z0-9_.-]+:(\s|$)", c)]
            if bad:
                raise ValueError(f"indented line under {key!r} looks like a mapping or list entry (missing parent key?): {bad[0]!r}")
            data[key] = " ".join([val] + cont)
    return data, body


def unquote(v):
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v


def check_skill(skill_dir):
    errors = []
    path = skill_dir / "SKILL.md"
    try:
        fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    except ValueError as e:
        return [f"{path}: {e}"]
    extra = sorted(set(fm) - SPEC_KEYS)
    if extra:
        errors.append(f"frontmatter keys outside the Agent Skills spec: {extra} (put agent-specific data under metadata)")
    name = unquote(strip_comment(fm["name"])) if isinstance(fm.get("name"), str) else ""
    if not name:
        errors.append("missing required field: name")
    else:
        if len(name) > 64 or not NAME_RE.match(name):
            errors.append(f"name {name!r} breaks the naming rule (a-z0-9, single hyphens, <=64)")
        if name != skill_dir.name:
            errors.append(f"name {name!r} does not match directory {skill_dir.name!r}")
    desc = fm.get("description")
    if not isinstance(desc, str) or not unquote(desc).strip():
        errors.append("missing required field: description")
    elif len(unquote(desc)) > 1024:
        errors.append(f"description is {len(unquote(desc))} chars (max 1024)")
    comp = fm.get("compatibility")
    if isinstance(comp, str) and not 1 <= len(unquote(comp)) <= 500:
        errors.append("compatibility must be 1-500 chars")
    if not isinstance(fm.get("license"), str) or not unquote(fm["license"]).strip():
        errors.append("missing field: license (gh skill publish warns on it)")
    meta = fm.get("metadata")
    if meta is not None and not isinstance(meta, dict):
        errors.append("metadata must be a map of string keys to string values")
    elif isinstance(meta, dict):
        for k, v in meta.items():
            quoted = len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]
            if not quoted and YAML_NON_STRING.match(v):
                errors.append(f"metadata.{k} = {v!r} would not load as a string in YAML; quote it")
    if isinstance(fm.get("allowed-tools"), (dict, list)) or str(fm.get("allowed-tools", "")).startswith("["):
        errors.append("allowed-tools must be a space-separated string, not a list")
    leaked = [k for k in meta if k.startswith(INSTALL_PREFIX)] if isinstance(meta, dict) else []
    if leaked:
        errors.append(f"install metadata present: {sorted(leaked)} (run gh skill publish --fix)")
    urls = URL_RE.findall(body)
    if urls:
        errors.append(f"SKILL.md links outside the skill ({urls[0]}); cite it, dated, in a reference file instead")
    n = len(body.splitlines())
    if n > 500:
        errors.append(f"SKILL.md body is {n} lines (recommended max 500)")
    root = skill_dir.resolve()
    for md in sorted(skill_dir.rglob("*.md")):
        for ref in sorted(set(REF_RE.findall(md.read_text(encoding="utf-8")))):
            target = (skill_dir / ref).resolve()
            if root not in target.parents:
                errors.append(f"{md.relative_to(skill_dir)}: reference `{ref}` points outside the skill folder")
            elif not target.is_file():
                errors.append(f"{md.relative_to(skill_dir)}: reference `{ref}` does not resolve inside the skill")
    return [f"{skill_dir.name}: {e}" for e in errors]


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def norm_version(v):
    """'0.6' and '0.6.0' name the same release: pad the numeric core to three parts and keep
    any pre-release or build suffix, so '1.0-beta' and '1.0.0-beta' compare equal. Applied to
    both sides of a comparison, so neither the skill nor the manifest form is privileged."""
    v = unquote(v)
    m = re.match(r"^(\d+(?:\.\d+)*)(.*)$", v)
    if not m:
        return v
    core = m.group(1).split(".")
    return ".".join(core + ["0"] * (3 - len(core))) + m.group(2)


def readme_words(text):
    return len(re.sub(r"```.*?```", " ", text, flags=re.S).split())


def check_plugin(plugin_dir):
    errors, where = [], f"plugins/{plugin_dir.name}"
    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    try:
        pj = json.loads(manifest.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{where}: missing .claude-plugin/plugin.json (Claude and the Directory need it)"]
    except json.JSONDecodeError as e:
        return [f"{where}: plugin.json is not valid JSON: {e}"]
    name = pj.get("name", "")
    if name != plugin_dir.name:
        errors.append(f"plugin.json name {name!r} does not match folder {plugin_dir.name!r}")
    if not NAME_RE.match(name or "") or len(name) > 64:
        errors.append(f"plugin name {name!r} breaks the naming rule (a-z0-9, single hyphens, <=64)")
    version = pj.get("version")
    if not isinstance(version, str) or not SEMVER_RE.match(version):
        errors.append(f"plugin.json version {version!r} is not x.y.z")
    if not pj.get("license") and not (plugin_dir / "LICENSE").is_file():
        errors.append("no licence: set license in plugin.json or add LICENSE (the Directory blocks without one)")
    readme = plugin_dir / "README.md"
    if not readme.is_file():
        errors.append("missing README.md (the Directory blocks without one)")
    elif readme_words(readme.read_text(encoding="utf-8")) < 40:
        errors.append("README.md has fewer than 40 words outside code blocks (the Directory blocks it)")
    if (plugin_dir / "bin").exists():
        errors.append("top-level bin/ stops claude.ai and Cowork from installing the plugin")
    errors += check_agent_plugin(plugin_dir, pj)
    for rel in DEV_ONLY:
        if list(plugin_dir.rglob(rel)):
            errors.append(f"development file {rel} inside the plugin: it would ship to every install; keep it outside plugins/")
    skills = sorted(plugin_dir.glob("skills/*/SKILL.md"))
    if not skills:
        errors.append("no skills/<name>/SKILL.md inside the plugin")
    for md in skills:
        try:
            fm, _ = parse_frontmatter(md.read_text(encoding="utf-8"))
        except ValueError:
            continue  # reported by check_skill
        meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
        sv = meta.get("version")
        if isinstance(version, str) and sv and norm_version(sv) != norm_version(version):
            errors.append(f"plugin.json version {version} does not match {md.parent.name} metadata.version {unquote(sv)}")
    return [f"{where}: {e}" for e in errors]


AGENT_PLUGINS_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
AGENT_PLUGINS_KEYS = {"$schema", "name", "version", "description", "author", "homepage",
                      "repository", "license", "keywords", "extensions"}
AGENT_PLUGINS_NAME = re.compile(r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
# Fields both manifests carry; they must agree, because each client reads only its own.
SHARED_FIELDS = ("name", "version", "description", "license", "repository", "keywords", "author")
# Files that steer development agents. Nothing under plugins/ may be one: that folder is
# what installs receive, and an installed agent would read these as its own instructions.
DEV_ONLY = ("AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "CLAUDE.local.md", "GEMINI.md",
            ".claude", ".cursor", ".windsurf", ".github")


def check_agent_plugin(plugin_dir, claude_manifest):
    """Agent Plugins 1.0.0 (agent-plugins.org): a root plugin.json with the pinned $schema,
    only the spec's fields, and the same values as the Claude manifest; mcp.json and
    .mcp.json, when either exists, declare the same servers."""
    errors = []
    path = plugin_dir / "plugin.json"
    try:
        ap = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ["missing root plugin.json (Agent Plugins 1.0.0 manifest)"]
    except json.JSONDecodeError as e:
        return [f"root plugin.json is not valid JSON: {e}"]
    if ap.get("$schema") != AGENT_PLUGINS_SCHEMA:
        errors.append(f"root plugin.json $schema must be {AGENT_PLUGINS_SCHEMA}")
    extra = sorted(set(ap) - AGENT_PLUGINS_KEYS)
    if extra:
        errors.append(f"root plugin.json has fields Agent Plugins 1.0.0 rejects: {extra} (client extras go under extensions)")
    if not AGENT_PLUGINS_NAME.match(str(ap.get("name", ""))) or len(str(ap.get("name", ""))) > 64:
        errors.append(f"root plugin.json name {ap.get('name')!r} breaks the Agent Plugins name rule")
    for field in SHARED_FIELDS:
        if field in ap or field in claude_manifest:
            if ap.get(field) != claude_manifest.get(field):
                errors.append(f"{field} differs between plugin.json and .claude-plugin/plugin.json")
    mcp_ap, mcp_claude = plugin_dir / "mcp.json", plugin_dir / ".mcp.json"
    if mcp_ap.exists() or mcp_claude.exists():
        try:
            a = json.loads(mcp_ap.read_text(encoding="utf-8")) if mcp_ap.exists() else None
            c = json.loads(mcp_claude.read_text(encoding="utf-8")) if mcp_claude.exists() else None
        except json.JSONDecodeError as e:
            return errors + [f"mcp.json or .mcp.json is not valid JSON: {e}"]
        if a is None or c is None:
            errors.append("mcp.json (Agent Plugins) and .mcp.json (Claude) must both exist, declaring the same servers")
        elif sorted((a.get("mcpServers") or {})) != sorted((c.get("mcpServers") or {})):
            errors.append("mcp.json and .mcp.json declare different servers")
    return errors


def check_marketplace(root, plugin_dirs):
    path = root / ".claude-plugin" / "marketplace.json"
    if not path.is_file():
        return []
    try:
        mp = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"marketplace.json is not valid JSON: {e}"]
    errors, listed = [], set()
    for entry in mp.get("plugins", []):
        src = entry.get("source")
        if not isinstance(src, str):
            continue  # remote sources are not checked here
        target = (root / src).resolve()
        if not (target / ".claude-plugin" / "plugin.json").is_file():
            errors.append(f"marketplace entry {entry.get('name')!r}: source {src!r} has no .claude-plugin/plugin.json")
            continue
        listed.add(target)
        if entry.get("name") != target.name:
            errors.append(f"marketplace entry {entry.get('name')!r} does not match folder {target.name!r}")
    for d in plugin_dirs:
        if d.resolve() not in listed:
            errors.append(f"plugins/{d.name} is not listed in marketplace.json")
    return errors


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    skills = sorted(p.parent for p in [*root.glob("skills/*/SKILL.md"), *root.glob("plugins/*/skills/*/SKILL.md")])
    if not skills:
        print("no skills found under plugins/*/skills/*/ or skills/*/", file=sys.stderr)
        return 1
    plugin_dirs = sorted(p for p in root.glob("plugins/*") if p.is_dir())
    errors = [e for s in skills for e in check_skill(s)]
    errors += [e for d in plugin_dirs for e in check_plugin(d)]
    errors += check_marketplace(root, plugin_dirs)
    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    print(f"checked {len(skills)} skill(s): {', '.join(s.name for s in skills)}; {len(plugin_dirs)} plugin(s); {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
