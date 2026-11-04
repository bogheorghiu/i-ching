#!/usr/bin/env python3
"""Keep tracked JSON files pure ASCII, with no \\uXXXX escape sequences.

Ported from bogheorghiu/ex-cog-dev (.github/scripts/); the history below is that
repository's.

Why this gate exists
--------------------
A JSON manifest here is machine-facing, but its `description` field is *prose* -
a sentence shown to a human browsing the marketplace. Prose attracts typographic
characters (em-dashes especially), and a non-ASCII character in a JSON file is
the input a whole class of silent rewrites needs:

  json.load(f) -> change one field -> json.dump(f)

Python's `json.dump` defaults to `ensure_ascii=True`, so that round trip re-emits
*every* non-ASCII character in the file as a `\\uXXXX` escape - including
characters on lines nobody was editing. It happened twice in ex-cog-dev (June
2026, two plugin manifests); one instance shipped and sat on main unnoticed for
over a month. The tool exits 0, the file still parses, the tests still pass, and
the change is semantically null: escaped and raw are the *same* JSON value, so
no consumer can tell. Only the bytes differ - which means only a diff, a grep, or
a byte check can see it.

Detecting that after the fact was the original plan. Removing the input is
better: with no non-ASCII character in the file, there is nothing to re-encode,
and the failure mode cannot occur at all. Hence "ASCII-only" rather than "no
escape sequences" - it is the blunter rule, and the one that cannot be argued
with.

Why it does NOT reformat
------------------------
The fixer replaces the offending *bytes* and nothing else. It never parses and
re-serialises the file, because that is the original defect wearing a fix's
clothes: rewriting a whole file to correct one line is exactly what produced the
damage this guard exists to prevent.

CI runs this WITHOUT --fix, so the job reports and fails but never modifies a
file. Rewriting files from CI would put an unreviewed whole-file write on the
publish path.

Scope: tracked `*.json` only. Markdown is deliberately untouched - prose
carries em-dashes as house style, nothing parses and re-serialises
Markdown, and this failure has never occurred there.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# The one character we substitute automatically. It is punctuation with an exact,
# meaning-preserving ASCII stand-in, and it is the character that caused every
# recorded instance. Anything else is a judgement call the operator makes.
EM_DASH = "—".encode()
EM_DASH_REPLACEMENT = b"-"

# The code point --fix knows how to substitute, in its escaped spelling. Compared
# numerically against a parsed escape rather than matched as a byte string: a plain
# substring search is blind to backslash parity and would corrupt a valid file (see
# replace_escaped_em_dash).
EM_DASH_CODE_POINT = 0x2014

# Experiment fixtures are excluded, and the reason is the opposite of the usual one:
# their bytes are the point. These files hold pre-registered probe stimuli for
# batteries that have already run, so "improving" a character in them silently
# changes the input of a completed experiment and makes before/after results
# non-comparable - a worse outcome than the typography this guard is tidying. They
# are also not manifests: nothing load-modify-redumps them, so the failure mode
# being guarded against cannot reach them.
# Adapted for this repository: the bundled Zhouyi text is excluded because its
# characters are its content. Escaping them to \uXXXX would keep the JSON value but
# leave the file unreadable to a person checking it against a printed or online copy,
# which is how this file gets verified. No manifest tool rewrites it.
# The folder, not the file, is named: the bundled text is the only JSON file in it.
EXCLUDED_PREFIXES = ("plugins/i-ching-reading/skills/i-ching-reading/references/",)

# An escaped non-ASCII character is pure ASCII on disk, so the non-ASCII scan below
# cannot see it - but it is precisely what the bad round trip *produces*, so it is
# caught separately.
#
# The `(?:\\\\)*` in the middle is load-bearing and easy to get wrong: what decides
# whether a backslash-u starts a real escape is whether the run of backslashes before
# it is EVEN (they pair off, so this one escapes the `u`) or ODD (the last one is
# itself escaped, so `u2014` is literal text). A single-character lookbehind gets the
# odd case right and the even case wrong - it misses a genuine escape that happens to
# follow an escaped backslash, e.g. a description containing `path\—end`, which is
# exactly what the round trip emits. Verified: the naive form finds nothing there.
ESCAPE_RE = re.compile(rb"(?<!\\)(?:\\\\)*\\u[0-9a-fA-F]{4}")

# A literal byte below 0x20 is invalid inside a JSON string, so a control character
# MUST be written escaped in some form - flagging those would make correct JSON
# unmergeable. An escape naming a code point below 0x20 is therefore allowed.
#
# (Not because backslash-u is the only spelling, which an earlier version of this
# comment claimed: JSON gives five control characters a shorter two-character escape
# - \b \t \n \f \r - and those are exactly what json.dump emits, so they are the
# common case rather than a corner. The regex above matches only the \uXXXX form, so
# the guard behaves identically either way; it was the stated reason that was false.)
#
# Everything at or above that boundary is flagged REGARDLESS of what it names - an
# HTML-safe serializer's `<` fails this guard exactly as an escaped em-dash does.
# That is deliberate, and the bluntness is the point: "is this a control character?"
# is decidable from the code point, "is this typography?" is not. A guard that tried
# to tell them apart would need a judgement call in a place that must not have one.
CONTROL_MAX = 0x20


def tracked_json_files(repo_root: Path) -> tuple[list[Path], list[str], list[str]]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "*.json"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    ).stdout

    seen: dict[str, None] = {}
    excluded: list[str] = []
    for raw in out.split(b"\0"):
        if not raw:
            continue
        rel = raw.decode()
        if rel.startswith(EXCLUDED_PREFIXES):
            excluded.append(rel)
            continue
        # `git ls-files` lists a path once per stage during an unresolved merge, so
        # the same file would otherwise be reported three times.
        seen.setdefault(rel, None)

    # A tracked path can be absent from the working tree mid-refactor (deleted but not
    # yet staged). Skip those rather than dying: this is the documented local
    # self-check, and a traceback instead of a report is a worse answer than "nothing
    # to check here". CI is unaffected - a fresh checkout has every tracked file.
    #
    # But SAY which ones were skipped. Silently narrowing the set and then printing
    # "ASCII-only" is the same defect as reporting success over an EMPTY set - the one
    # the guard in main() refuses - just at N>0 instead of N=0. A partial scan that
    # reads as a full pass is how an unchecked file acquires a green tick.
    present: list[Path] = []
    skipped: list[str] = []
    for rel in seen:
        path = repo_root / rel
        if path.is_file():
            present.append(path)
        else:
            skipped.append(rel)
            print(f"skipped (tracked, not in working tree): {rel}", file=sys.stderr)
    return present, skipped, excluded


def write_atomically(path: Path, data: bytes) -> None:
    """Replace `path`'s contents all-or-nothing.

    `Path.write_bytes` truncates first and then writes, so an interruption between
    the two - Ctrl-C, a full disk - leaves the file empty or half-written. For a
    plugin manifest that is worse than the typography this tool exists to tidy, and
    it would make the guard against programs corrupting manifests into a program
    that corrupts one.

    Writing a sibling temp file and renaming it over the target avoids that: the
    rename is atomic, so a reader sees either the old bytes or the new ones and
    never a partial file. The temp file must be in the SAME directory - `os.replace`
    is only atomic within one filesystem, and /tmp is often a different one.
    """
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        # If the rename never happened, don't leave the scratch file behind.
        if tmp.exists():
            tmp.unlink()


def line_of(data: bytes, index: int) -> int:
    return data.count(b"\n", 0, index) + 1


def replace_escaped_em_dash(data: bytes) -> bytes:
    """Replace genuine escaped em-dashes with '-', respecting backslash parity.

    Both spellings of the character are fixed - raw and escaped - because the bad
    round trip emits the escaped one, and an operator told to run --fix on "an
    em-dash" should not have to care which form is on disk.

    It must go through the same regex the scanner uses, NOT a substring replace.
    A substring search for the six bytes of the escape also matches the tail of an
    escaped backslash followed by the literal text `u2014` - which is not an escape
    at all - starting the match at the second backslash. Replacing there emits a
    lone backslash followed by '-', which is not a legal JSON escape, so a valid
    file stops parsing. That is the same "a tool rewrote bytes it did not
    understand" failure this whole guard exists to prevent, so the fixer must not
    commit it.
    """

    def substitute(match: re.Match[bytes]) -> bytes:
        token = match.group()
        if int(token[-4:], 16) != EM_DASH_CODE_POINT:
            return token
        # Keep any leading escaped-backslash pairs; only the escape itself goes.
        return token[:-6] + EM_DASH_REPLACEMENT

    return ESCAPE_RE.sub(substitute, data)


def scan(data: bytes) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """Return (non_ascii, escapes) as lists of (line_number, detail)."""
    non_ascii: list[tuple[int, str]] = []
    for match in re.finditer(rb"[^\x00-\x7F]+", data):
        text = match.group().decode("utf-8", errors="replace")
        for ch in dict.fromkeys(text):  # unique, order-preserving
            non_ascii.append((line_of(data, match.start()), f"U+{ord(ch):04X} {ch!r}"))

    escapes: list[tuple[int, str]] = []
    for m in ESCAPE_RE.finditer(data):
        token = m.group().decode("ascii")
        # The match may carry leading escaped-backslash pairs; the escape itself is
        # always the trailing 6 characters.
        code_point = int(token[-4:], 16)
        if code_point < CONTROL_MAX:
            continue
        escapes.append((line_of(data, m.start()), token[-6:]))
    return non_ascii, escapes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Replace em-dashes with '-' in place, in BOTH spellings - the raw "
        "character and its escaped form (byte substitution, no reformatting). Any "
        "other non-ASCII character is reported and left alone: it needs a human "
        "decision, not a default.",
    )
    args = parser.parse_args()

    repo_root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    )

    files, skipped, excluded = tracked_json_files(repo_root)

    # Fail loudly on an empty file set rather than reporting success over nothing.
    # A guard that inspects zero files prints the same "all clear" as one that
    # inspected everything and found nothing - so a broken invocation (wrong cwd,
    # a glob that stops matching, a checkout that did not happen) would read as a
    # green tick forever. This repo always tracks JSON manifests; zero means the
    # scan is broken, not that the tree is clean.
    if not files:
        print(
            "No tracked JSON files found - refusing to report success.\n"
            "This guard is meaningless over an empty set; check the working "
            "directory and that the repository is checked out.",
            file=sys.stderr,
        )
        return 1

    failures = 0
    fixed_files = 0

    for path in files:
        data = path.read_bytes()

        if args.fix:
            fixed = replace_escaped_em_dash(data.replace(EM_DASH, EM_DASH_REPLACEMENT))
            # Gate the write on an actual change, not on a substring test. The old
            # gate could fire on a file with nothing to fix and rewrite it anyway.
            if fixed != data:
                write_atomically(path, fixed)
                data = fixed
                fixed_files += 1
                print(f"fixed (em-dash -> '-'): {path.relative_to(repo_root)}")

        non_ascii, escapes = scan(data)
        rel = path.relative_to(repo_root)

        for line, detail in non_ascii:
            failures += 1
            print(f"{rel}:{line}: non-ASCII character {detail}", file=sys.stderr)
        for line, detail in escapes:
            failures += 1
            print(f"{rel}:{line}: escape sequence {detail}", file=sys.stderr)

    if failures:
        print(
            f"\n{failures} problem(s) found in tracked JSON.\n"
            "  Em-dashes:  python3 .github/scripts/check_json_ascii.py --fix\n"
            "  Anything else: decide deliberately, then edit the character in place.\n"
            "    Do NOT reformat the file or pipe it through a JSON dumper - a whole-file\n"
            "    rewrite to fix one character is the defect this guard exists to prevent.",
            file=sys.stderr,
        )
        return 1

    # Claim "clean" only about what was actually opened. `tracked_json_files` argues
    # that a partial scan reading as a full pass is the same defect as reporting
    # success over an empty set - so the final line has to carry that qualifier, or
    # the code is making an argument it does not keep one screen later.
    # Two ways the scan is short of "every tracked .json", and both belong in the line:
    # a file git lists but the tree does not have, and a file EXCLUDED_PREFIXES drops
    # before it is ever opened. Only the first was reported, so a clean run over a tree
    # containing unscanned probe fixtures still printed the unqualified claim.
    short = []
    if skipped:
        short.append(f"{len(skipped)} tracked file(s) SKIPPED")
    if excluded:
        short.append(f"{len(excluded)} exempt file(s) not scanned")
    scope = "" if not short else " — " + ", ".join(short) + "; not a full scan"
    if fixed_files:
        print(f"\n{fixed_files} file(s) fixed; the files scanned are ASCII-only.{scope}")
    else:
        print(f"The files scanned are ASCII-only, with no escape sequences.{scope}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
