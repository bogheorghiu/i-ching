#!/usr/bin/env python3
"""The skill's data agrees with itself and with the bundled Zhouyi text.

Ported from the 2026-11-02 claims audit's checks.py (personal-use-tools, branch
archive/i-ching-audit-2026-11-02). Ground truth for each hexagram's line pattern is the
line markers in the bundled text (初九/九二/.../上六: 九 = yang, 六 = yin), so a wrong
entry in any table is caught against the text, not against another table.

Run from the repository root: python3 tests/test_skill_data.py
"""
import collections
import itertools
import json
import os
import re
import sys
import unittest
from fractions import Fraction
from unittest import mock

SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugins",
                     "i-ching-reading", "skills", "i-ching-reading")
sys.path.insert(0, os.path.join(SKILL, "scripts"))
import yarrow_simulation as ys  # noqa: E402

POS = ["初", "二", "三", "四", "五", "上"]
MARKER = re.compile(r"^(初|上)(九|六)|^(九|六)(二|三|四|五)")
SYM = {"☰": (1, 1, 1), "☷": (0, 0, 0), "☳": (1, 0, 0), "☵": (0, 1, 0),
       "☶": (0, 0, 1), "☴": (0, 1, 1), "☲": (1, 0, 1), "☱": (1, 1, 0)}


def read(rel):
    with open(os.path.join(SKILL, rel), encoding="utf-8") as f:
        return f.read()


def patterns_from_text():
    """{King Wen number: (line1..line6 as 1/0)} from the source text's line markers."""
    src = json.loads(read("references/zhouyi-source.json"))
    pats, errors = {}, []
    for h in src["hexagrams"]:
        bits = []
        for i, line in enumerate(h["lines_zh"]):
            m = MARKER.match(line)
            if not m:
                errors.append((h["kw"], i + 1, line[:6]))
                continue
            pos, val = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
            if POS.index(pos) != i:
                errors.append((h["kw"], i + 1, "position " + pos))
            bits.append(1 if val == "九" else 0)
        pats[h["kw"]] = tuple(bits)
    return pats, errors


PAT, MARKER_ERRORS = patterns_from_text()
INV = {v: k for k, v in PAT.items()}


def stable(bits):
    return [7 if b else 8 for b in bits]


def exact_distribution(fn, n):
    """Run fn once for every value random.randint(0, n - 1) can return."""
    counts = collections.Counter()
    for r in range(n):
        with mock.patch.object(ys.random, "randint", return_value=r):
            counts[fn()] += 1
    return {k: Fraction(v, n) for k, v in counts.items()}


class SourceText(unittest.TestCase):
    def test_every_line_has_a_marker_in_its_position(self):
        self.assertEqual(MARKER_ERRORS, [])

    def test_sixty_four_distinct_six_line_patterns(self):
        self.assertEqual(sorted(PAT), list(range(1, 65)))
        self.assertTrue(all(len(p) == 6 for p in PAT.values()))
        self.assertEqual(len(set(PAT.values())), 64)


class ScriptTablesMatchText(unittest.TestCase):
    def test_king_wen_lookup(self):
        bad = [(kw, ys.get_hexagram_number(p[:3], p[3:])) for kw, p in PAT.items()
               if ys.get_hexagram_number(p[:3], p[3:]) != kw]
        self.assertEqual(bad, [])

    def test_hexagram_table_has_all_64(self):
        self.assertEqual(sorted(ys.HEXAGRAMS), list(range(1, 65)))

    def test_nuclear(self):
        bad = []
        for kw, p in PAT.items():
            expected = INV[(p[1], p[2], p[3], p[2], p[3], p[4])]
            got = ys.nuclear_hexagram(stable(p))[0]
            if got != expected:
                bad.append((kw, got, expected))
        self.assertEqual(bad, [])

    def test_complementary(self):
        bad = [kw for kw, p in PAT.items()
               if ys.complementary_hexagram(stable(p)) != INV[tuple(1 - b for b in p)]]
        self.assertEqual(bad, [])

    def test_king_wen_pairs_are_reversals_or_inversions(self):
        neither = []
        for k in range(1, 65, 2):
            a, b = PAT[k], PAT[k + 1]
            if not ((a[::-1] == b and a != b) or tuple(1 - x for x in a) == b):
                neither.append(k)
        self.assertEqual(neither, [])

    def test_xor_layer_equals_changed_line_for_all_4096_casts(self):
        for cast in itertools.product((6, 7, 8, 9), repeat=6):
            via_change = [1 if ys.changed_line(v) in (7, 9) else 0 for v in cast]
            via_xor = [v ^ c for v, c in map(ys.value_to_vc, cast)]
            self.assertEqual(via_change, via_xor, cast)


class CastingProbabilities(unittest.TestCase):
    def test_yarrow_is_1_5_7_3_sixteenths(self):
        self.assertEqual(exact_distribution(ys.yarrow_line, 16),
                         {6: Fraction(1, 16), 7: Fraction(5, 16), 8: Fraction(7, 16), 9: Fraction(3, 16)})

    def test_coins_are_1_3_3_1_eighths(self):
        self.assertEqual(exact_distribution(ys.coin_line, 8),
                         {6: Fraction(1, 8), 7: Fraction(3, 8), 8: Fraction(3, 8), 9: Fraction(1, 8)})


class ReferenceFilesMatchText(unittest.TestCase):
    def test_trigram_dynamics_numbers(self):
        checked, bad = 0, []
        for i, line in enumerate(read("references/trigram-dynamics.md").splitlines(), 1):
            m = re.search(r"\*\*(\S) over (\S) \([^)]*\):\*\* ([^(]+)\((\d+)\)", line)
            if m:
                checked += 1
                if INV[SYM[m.group(2)] + SYM[m.group(1)]] != int(m.group(4)):
                    bad.append(i)
            m = re.search(r"\*\*(\S)(\S) \S+ \((\d+)\):\*\*", line)
            if m and m.group(1) in SYM:
                checked += 1
                if INV[SYM[m.group(1)] * 2] != int(m.group(3)):
                    bad.append(i)
        # 56 pair entries plus 8 doubled trigrams: fewer means a reformatted line went unchecked.
        self.assertEqual(checked, 64)
        self.assertEqual(bad, [])

    def test_compendium_trigrams_pairs_and_nuclears(self):
        nuclear = {kw: INV[(p[1], p[2], p[3], p[2], p[3], p[4])] for kw, p in PAT.items()}
        cur, bad, checked = None, [], collections.Counter()
        for i, line in enumerate(read("references/hexagram-compendium.md").splitlines(), 1):
            m = re.match(r"^### (\d+)\. ", line)
            if m:
                cur = int(m.group(1))
                continue
            if cur is None:
                continue
            m = re.match(r"^\*\*(\S) over (\S) ", line)
            if m and m.group(1) in SYM:
                checked["trigrams"] += 1
                if INV[SYM[m.group(2)] + SYM[m.group(1)]] != cur:
                    bad.append((i, "trigrams"))
            m = re.match(r"^\*\*Pair:\*\* (\d+)", line)
            if m:
                checked["pair"] += 1
                if int(m.group(1)) != (cur + 1 if cur % 2 else cur - 1):
                    bad.append((i, "pair"))
            for m in re.finditer(r"[Nn]uclear(?: hexagram)?(?: is|:) (\d+)", line):
                checked["nuclear"] += 1
                if int(m.group(1)) != nuclear[cur]:
                    bad.append((i, "nuclear"))
        self.assertEqual(checked["trigrams"], 64, checked)
        self.assertEqual(checked["pair"], 64, checked)
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
