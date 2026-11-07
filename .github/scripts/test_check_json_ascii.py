#!/usr/bin/env python3
"""Unit tests for the JSON ASCII guard's detection AND fixing logic.

Pure-function tests against `scan()` (detection) and `replace_escaped_em_dash()`
(the byte substitution `--fix` performs) - no git, no filesystem. Both are named
because a suite sitting beside its subject is what answers "is this tested?", so
a header that mentions only detection tells the next reader the fixer is
uncovered when three of these cases exercise it. Run directly:
    python3 .github/scripts/test_check_json_ascii.py

The case that matters most is `test_escape_after_escaped_backslash`: the guard's
first version used a single-character negative lookbehind and silently missed a
genuine escape that followed an escaped backslash - a miss produced by the exact
`json.dump` round trip the guard exists to catch. A guard with a hole in it is
worse than no guard, because it reports clean. That case is the regression test.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from check_json_ascii import replace_escaped_em_dash, scan  # noqa: E402

failures = []

# Built from pieces so the six-character escape survives being written, sent through
# a tool call, and read back. Writing it literally is unreliable: the notation is
# itself meaningful to the JSON transport that carries this file's contents, which is
# the same class of bug the guard detects.
ESC = "\\" + "u2014"


def check(name, cond):
    if cond:
        print(f"   ✓ {name}")
    else:
        print(f"   ✗ {name}")
        failures.append(name)


def test_clean():
    print("\n1. clean ASCII JSON -> no findings")
    non_ascii, escapes = scan(b'{"description": "plain - hyphen only"}')
    check("no non-ASCII", non_ascii == [])
    check("no escapes", escapes == [])


def test_raw_non_ascii():
    print("\n2. raw em-dash -> reported as non-ASCII")
    non_ascii, escapes = scan('{"d": "a — b"}'.encode())
    check("one non-ASCII finding", len(non_ascii) == 1)
    check("identified as U+2014", "U+2014" in non_ascii[0][1])
    check("not double-reported as an escape", escapes == [])


def test_escaped_form():
    print("\n3. escaped em-dash -> reported as an escape")
    non_ascii, escapes = scan(('{"d": "a ' + ESC + ' b"}').encode())
    check("no non-ASCII (the escape is pure ASCII on disk)", non_ascii == [])
    check("one escape finding", len(escapes) == 1)
    check("token reported", escapes[0][1] == ESC)


def test_escape_after_escaped_backslash():
    print("\n4. REGRESSION: escape preceded by an escaped backslash is still caught")
    # A description ending in a backslash, round-tripped exactly as the bug does it.
    data = json.dumps({"d": "path\\—end"}).encode()
    non_ascii, escapes = scan(data)
    check("the round trip really produced an escape", ESC.encode() in data)
    check("guard catches it (single-char lookbehind missed this)", len(escapes) == 1)


def test_literal_u_is_not_an_escape():
    print("\n5. escaped backslash followed by literal 'u2014' -> NOT an escape")
    # In JSON this is a backslash then the text u2014, not a character escape.
    non_ascii, escapes = scan(b'{"d": "a \\\\u2014 b"}')
    check("no escape reported", escapes == [])


def test_control_escapes_allowed():
    print("\n6. control-character escapes are allowed (JSON has no other spelling)")
    for token, label in (("\\" + "u0007", "BEL"), ("\\" + "u001F", "unit separator")):
        _, escapes = scan(('{"d": "x' + token + 'y"}').encode())
        check(f"{label} escape permitted", escapes == [])


def test_non_control_escape_still_flagged():
    print("\n7. a non-control escape just above the boundary is still flagged")
    _, escapes = scan(('{"d": "x' + "\\" + 'u0020y"}').encode())
    check("U+0020 (space) is not a control char, so it is flagged", len(escapes) == 1)


def test_fix_respects_backslash_parity():
    print("\n9. REGRESSION: --fix must not corrupt a file the scanner deliberately ignores")
    # Escaped backslash then the literal text u2014 - NOT an escape (see case 5).
    # A substring replace would match from the second backslash and emit `\-`,
    # which is not a legal JSON escape, so the file would stop parsing.
    data = b'{"d": "a \\\\u2014 b"}'
    out = replace_escaped_em_dash(data)
    check("left untouched", out == data)
    try:
        json.loads(out.decode())
        check("still parses as JSON", True)
    except ValueError:
        check("still parses as JSON", False)


def test_fix_replaces_real_escape():
    print("\n10. --fix does replace a genuine escaped em-dash")
    out = replace_escaped_em_dash(('{"d": "a ' + ESC + ' b"}').encode())
    check("escape became a hyphen", out == b'{"d": "a - b"}')


def test_fix_preserves_leading_escaped_backslash():
    print("\n11. --fix keeps an escaped backslash that precedes a real escape")
    # `\\` (an escaped backslash) followed by a genuine escaped em-dash.
    out = replace_escaped_em_dash(b'{"d": "a \\\\\\u2014 b"}')
    check("backslash pair preserved, escape replaced", out == b'{"d": "a \\\\- b"}')
    try:
        json.loads(out.decode())
        check("still parses as JSON", True)
    except ValueError:
        check("still parses as JSON", False)


def test_line_numbers():
    print("\n8. findings carry the right line number")
    non_ascii, _ = scan('{\n  "a": 1,\n  "d": "—"\n}'.encode())
    check("reported on line 3", non_ascii and non_ascii[0][0] == 3)


for fn in (
    test_clean,
    test_raw_non_ascii,
    test_escaped_form,
    test_escape_after_escaped_backslash,
    test_literal_u_is_not_an_escape,
    test_control_escapes_allowed,
    test_non_control_escape_still_flagged,
    test_line_numbers,
    test_fix_respects_backslash_parity,
    test_fix_replaces_real_escape,
    test_fix_preserves_leading_escaped_backslash,
):
    fn()

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("All JSON ASCII guard checks passed.")
