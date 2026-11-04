#!/usr/bin/env python3
"""Version-bump guard (ported from bogheorghiu/ex-cog-dev, .github/scripts/).

Fails a PR when files under a plugin directory changed but that plugin's
`.claude-plugin/plugin.json` `version` did not increase. The plugin version is
what `claude plugin update` keys on; a code/doc change shipped without a bump is
silently skipped by installs (the regression this guard prevents).

Usage (CI):
    python3 .github/scripts/check_version_bump.py <base_ref> [<head_ref>]

The decision logic (`evaluate`, `skip_requested`) is pure and unit-tested in
`test_check_version_bump.py`; the git plumbing is a thin wrapper around it.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Top-level plugin dirs in this marketplace and the prefix that "belongs" to
# each. A change to any tracked file under the prefix requires a version bump
# in that plugin's manifest.
#
# DERIVED FROM THE TREE, never hand-listed. A plugin IS a top-level directory
# with a `.claude-plugin/plugin.json`, so that glob is the definition - and a
# hardcoded list of the four that existed when this was written would fail in
# the one direction that matters: a fifth plugin would be absent from the map,
# the guard would find no relevant change under a name it does not know, and it
# would pass green while a REQUIRED rule was being broken. Silent under-coverage
# in a gate reads exactly like compliance.
def discover_plugin_dirs(root=None):
    """Map plugin name -> path prefix, for every top-level plugin in the repo."""
    base = Path(root) if root else Path(__file__).resolve().parents[2]
    # This repository keeps its plugins under plugins/<name>/ (ex-cog-dev keeps them
    # at the top level); the definition is otherwise unchanged.
    return {
        manifest.parents[1].name: f"plugins/{manifest.parents[1].name}/"
        for manifest in sorted(base.glob("plugins/*/.claude-plugin/plugin.json"))
    }


PLUGIN_DIRS = discover_plugin_dirs()

# Deliberate opt-out for genuine no-ops: a PR may skip the guard by putting this
# marker in its title or applying this label. The CI workflow forwards the PR
# title (PR_TITLE) and labels as a JSON array (PR_LABELS).
SKIP_MARKER = "[skip-version-bump]"
SKIP_LABEL = "skip-version-bump"


def version_tuple(v):
    """Parse a dotted version into an int tuple. (0,) for unparseable/None.

    Avoids the string-ordering trap where "1.9" > "1.10" alphabetically.
    """
    try:
        return tuple(int(p) for p in str(v).split("."))
    except (ValueError, AttributeError):
        return (0,)


def evaluate(changed_files, base_versions, head_versions, plugin_dirs=PLUGIN_DIRS):
    """Pure guard decision. Returns a list of failure messages ([] == pass).

    - changed_files: paths changed in the PR, relative to repo root.
    - base_versions / head_versions: {plugin_name: version_str_or_None} at the
      base and head refs (None = manifest absent or unparseable).
    - plugin_dirs: {plugin_name: dir_prefix}.

    Rules per plugin whose files changed:
    - manifest missing/unparseable at head  -> fail.
    - new plugin (absent at base, present at head) -> pass (any version ok).
    - head version must be strictly greater than base version -> else fail.
    """
    failures = []
    for name, prefix in plugin_dirs.items():
        touched = [f for f in changed_files if f.startswith(prefix)]
        if not touched:
            continue
        head_v = head_versions.get(name)
        base_v = base_versions.get(name)
        if head_v is None:
            failures.append(
                f"{name}: {len(touched)} file(s) changed under {prefix} but its "
                f".claude-plugin/plugin.json version is missing or unparseable at HEAD."
            )
            continue
        if base_v is None:
            # New plugin introduced in this PR — any version is acceptable.
            continue
        if version_tuple(head_v) <= version_tuple(base_v):
            failures.append(
                f"{name}: {len(touched)} file(s) changed under {prefix} but version did "
                f"not increase ({base_v} -> {head_v}). Bump {prefix}.claude-plugin/plugin.json."
            )
    return failures


def skip_requested(title, labels, marker=SKIP_MARKER, label_name=SKIP_LABEL):
    """True if the PR opted out via the title marker or the skip label.

    Both comparisons are case-insensitive; labels are trimmed. Tolerant of
    None / empty inputs (treated as "no opt-out").
    """
    if marker.lower() in (title or "").lower():
        return True
    return any((lbl or "").strip().lower() == label_name.lower() for lbl in (labels or []))


def _pr_labels_from_env():
    """Parse PR_LABELS (a JSON array of label names) from the environment."""
    try:
        parsed = json.loads(os.environ.get("PR_LABELS", "[]"))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _read_version(ref, prefix):
    """Read a plugin's manifest version at a git ref; None if absent/unparseable."""
    path = f"{prefix}.claude-plugin/plugin.json"
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None  # manifest does not exist at this ref
    try:
        return json.loads(proc.stdout).get("version")
    except json.JSONDecodeError:
        return None


def _changed_files(base_ref, head_ref):
    """Files changed between the merge-base of base_ref..head_ref and head_ref."""
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def main(argv):
    if not (2 <= len(argv) <= 3):
        print("usage: check_version_bump.py <base_ref> [<head_ref>]", file=sys.stderr)
        return 2
    base_ref = argv[1]
    head_ref = argv[2] if len(argv) == 3 else "HEAD"

    changed = _changed_files(base_ref, head_ref)
    base_versions = {n: _read_version(base_ref, p) for n, p in PLUGIN_DIRS.items()}
    head_versions = {n: _read_version(head_ref, p) for n, p in PLUGIN_DIRS.items()}
    failures = evaluate(changed, base_versions, head_versions)

    # Opt-out short-circuit. Still report what WOULD have failed, for transparency.
    if skip_requested(os.environ.get("PR_TITLE", ""), _pr_labels_from_env()):
        print(f"⏭️  Version-bump guard skipped via opt-out ({SKIP_MARKER} / {SKIP_LABEL} label).")
        for f in failures:
            print(f"   (would otherwise flag) {f}")
        return 0

    if failures:
        print("❌ Version-bump guard FAILED:")
        for f in failures:
            print(f"   - {f}")
        print(
            "\nAny change to a plugin's files must bump that plugin's "
            ".claude-plugin/plugin.json version, so `claude plugin update` picks it up."
            f"\nGenuine no-op? Add '{SKIP_MARKER}' to the PR title or the "
            f"'{SKIP_LABEL}' label to bypass."
        )
        return 1
    print("✅ Version-bump guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
