"""
The ALL LINES CHANGING structural note must agree with the skill's own method
(references/changing-lines.md, "Six Changing Lines") and with the source text:
Hexagrams 1 and 2 carry an extra statement for the all-changing case
(用九 / 用六 in references/zhouyi-source.json), so for them the note must point
to that statement instead of only saying "read the resulting hexagram".
"""
import os
import sys
import unittest
from unittest import mock

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "plugins", "i-ching-reading", "skills", "i-ching-reading", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))

import yarrow_simulation as y  # noqa: E402


def _reading_with_lines(lines):
    it = iter(lines)
    with mock.patch.object(y, "yarrow_line", lambda: next(it)):
        return y.generate_reading(method="yarrow", seed=0)


def _all_changing_note(reading):
    return [n for n in reading["structural_notes"] if n.startswith("ALL LINES CHANGING")]


class TestAllChangingNote(unittest.TestCase):
    def test_hexagram_1_all_changing_points_to_yong_jiu(self):
        r = _reading_with_lines([9] * 6)
        self.assertEqual(r["primary_hexagram"]["number"], 1)
        note = _all_changing_note(r)
        self.assertEqual(len(note), 1)
        self.assertIn("用九", note[0])

    def test_hexagram_2_all_changing_points_to_yong_liu(self):
        r = _reading_with_lines([6] * 6)
        self.assertEqual(r["primary_hexagram"]["number"], 2)
        note = _all_changing_note(r)
        self.assertEqual(len(note), 1)
        self.assertIn("用六", note[0])

    def test_other_all_changing_hexagram_keeps_the_general_rule(self):
        # 9,9,9,6,6,6 = Qian below, Kun above = Hexagram 11
        r = _reading_with_lines([9, 9, 9, 6, 6, 6])
        self.assertEqual(r["primary_hexagram"]["number"], 11)
        note = _all_changing_note(r)
        self.assertEqual(len(note), 1)
        self.assertNotIn("用九", note[0])
        self.assertNotIn("用六", note[0])
        self.assertIn("read the resulting hexagram", note[0])


if __name__ == "__main__":
    unittest.main()
