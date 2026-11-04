#!/usr/bin/env python3
"""Unit tests for the version-bump guard decision logic (ported from bogheorghiu/ex-cog-dev).

Mostly pure-function tests — no git. One exception, deliberately: the plugin-map
discovery test builds a temp tree and globs the real checkout, because the thing
being asserted is precisely that the map comes from the filesystem rather than a
hand-kept list. Importing the subject touches the filesystem too, since
`PLUGIN_DIRS` is computed at module scope. Run directly:
    python3 .github/scripts/test_check_version_bump.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_version_bump import (  # noqa: E402
    evaluate, version_tuple, skip_requested, discover_plugin_dirs,
)

DIRS = {"alpha": "alpha/", "beta": "beta/"}
failures = []


def check(name, cond):
    if cond:
        print(f"   ✓ {name}")
    else:
        print(f"   ✗ {name}")
        failures.append(name)


def test_version_tuple():
    print("\n1. version_tuple() comparison")
    check("1.10 > 1.9 numerically (not string)", version_tuple("1.10") > version_tuple("1.9"))
    check("2.0 > 1.99", version_tuple("2.0") > version_tuple("1.99"))
    check("equal versions compare equal", version_tuple("1.2.3") == version_tuple("1.2.3"))
    check("None -> (0,) fallback", version_tuple(None) == (0,))
    check("garbage -> (0,) fallback", version_tuple("x.y") == (0,))


def test_no_plugin_touched():
    print("\n2. changes outside any plugin dir -> pass")
    out = evaluate(
        [".github/workflows/ci.yml", "README.md"],
        {"alpha": "1.0.0", "beta": "1.0.0"},
        {"alpha": "1.0.0", "beta": "1.0.0"},
        DIRS,
    )
    check("no failures", out == [])


def test_bumped_passes():
    print("\n3. plugin changed + version bumped -> pass")
    out = evaluate(
        ["alpha/skills/x.md"],
        {"alpha": "1.0.0"},
        {"alpha": "1.0.1"},
        DIRS,
    )
    check("no failures", out == [])


def test_not_bumped_fails():
    print("\n4. plugin changed + version unchanged -> fail")
    out = evaluate(["alpha/skills/x.md"], {"alpha": "1.0.0"}, {"alpha": "1.0.0"}, DIRS)
    check("one failure", len(out) == 1)
    check("names the plugin", out and "alpha" in out[0])


def test_decreased_fails():
    print("\n5. plugin changed + version decreased -> fail")
    out = evaluate(["alpha/x"], {"alpha": "2.0.0"}, {"alpha": "1.9.0"}, DIRS)
    check("one failure", len(out) == 1)


def test_minor_vs_patch_ordering():
    print("\n6. 1.9 -> 1.10 counts as an increase (numeric, not string)")
    out = evaluate(["alpha/x"], {"alpha": "1.9"}, {"alpha": "1.10"}, DIRS)
    check("no failures (1.10 > 1.9)", out == [])


def test_missing_head_manifest_fails():
    print("\n7. plugin changed + manifest missing/unparseable at head -> fail")
    out = evaluate(["alpha/x"], {"alpha": "1.0.0"}, {"alpha": None}, DIRS)
    check("one failure", len(out) == 1)
    check("mentions missing/unparseable", out and "missing or unparseable" in out[0])


def test_new_plugin_passes():
    print("\n8. new plugin (absent at base) -> pass at any version")
    out = evaluate(["beta/x"], {"alpha": "1.0.0", "beta": None}, {"alpha": "1.0.0", "beta": "0.1.0"}, DIRS)
    check("no failures", out == [])


def test_multiple_plugins_independent():
    print("\n9. two plugins changed, only one bumped -> exactly one failure")
    out = evaluate(
        ["alpha/x", "beta/y"],
        {"alpha": "1.0.0", "beta": "1.0.0"},
        {"alpha": "1.0.1", "beta": "1.0.0"},  # alpha bumped, beta not
        DIRS,
    )
    check("exactly one failure", len(out) == 1)
    check("the failure is beta", out and "beta" in out[0] and "alpha" not in out[0])


def test_prefix_not_substring_matched():
    print("\n10. prefix matching is dir-anchored (alpha/ does not match alphabet/)")
    dirs = {"alpha": "alpha/"}
    out = evaluate(["alphabet/x.md"], {"alpha": "1.0.0"}, {"alpha": "1.0.0"}, dirs)
    check("no failures (alphabet/ is not under alpha/)", out == [])


def test_skip_requested():
    print("\n11. skip_requested() opt-out via title marker or label")
    check("title marker -> skip", skip_requested("fix typo [skip-version-bump]", []) is True)
    check("title marker case-insensitive", skip_requested("X [SKIP-VERSION-BUMP]", []) is True)
    check("label -> skip", skip_requested("plain title", ["skip-version-bump"]) is True)
    check("label case/space-insensitive", skip_requested("t", ["  Skip-Version-Bump "]) is True)
    check("unrelated label -> no skip", skip_requested("t", ["bug", "enhancement"]) is False)
    check("no marker/label -> no skip", skip_requested("ordinary title", []) is False)
    check("None inputs tolerated", skip_requested(None, None) is False)
    check("marker only matched bracketed, not bare word", skip_requested("version bump done", []) is False)


def test_plugin_dirs_derived_from_tree():
    """The plugin map must come from the filesystem, never a hand-kept list.

    This is the test the guard was missing. `PLUGIN_DIRS` used to be four hardcoded
    names, so a fifth plugin would simply be absent from the map: the guard would
    find no relevant change under a directory it did not know about and pass green,
    while the REQUIRED version-bump rule was being broken. Under-coverage in a gate
    is indistinguishable from compliance, which is the worst way for a gate to fail.
    """
    import tempfile

    print("\n12. PLUGIN_DIRS is derived from the tree, not hand-listed")
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for name in ("alpha", "beta", "fifth-toolkit"):
            (root / "plugins" / name / ".claude-plugin").mkdir(parents=True)
            (root / "plugins" / name / ".claude-plugin" / "plugin.json").write_text("{}")
        (root / "plugins" / "not-a-plugin").mkdir()  # no manifest -> must not appear
        got = discover_plugin_dirs(root)

    check("finds every dir with a manifest", sorted(got) == ["alpha", "beta", "fifth-toolkit"])
    check("a newly added plugin is picked up", "fifth-toolkit" in got)
    check("a dir without a manifest is excluded", "not-a-plugin" not in got)
    check("prefixes are plugins/<name>/", all(v == f"plugins/{k}/" for k, v in got.items()))
    real = discover_plugin_dirs()
    check("discovers this repo's own plugin", "i-ching-reading" in real)


if __name__ == "__main__":
    print("Testing version-bump guard logic (ported from bogheorghiu/ex-cog-dev)...")
    test_version_tuple()
    test_no_plugin_touched()
    test_bumped_passes()
    test_not_bumped_fails()
    test_decreased_fails()
    test_minor_vs_patch_ordering()
    test_missing_head_manifest_fails()
    test_new_plugin_passes()
    test_multiple_plugins_independent()
    test_prefix_not_substring_matched()
    test_skip_requested()
    test_plugin_dirs_derived_from_tree()
    if failures:
        print(f"\n❌ {len(failures)} check(s) failed: {failures}")
        raise SystemExit(1)
    print("\n✅ All version-bump-guard logic tests passed!")
