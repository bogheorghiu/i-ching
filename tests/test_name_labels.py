"""
The second English name per hexagram (Force, Field, ...) is not Alfred Huang's:
Huang's names for 1-3 are Initiating, Responding, Beginning. The text output
must not credit that set to Huang. The JSON key `huang_name` is left as it is,
so existing consumers of --json keep working.
"""
import os
import sys
import unittest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "plugins", "i-ching-reading", "skills", "i-ching-reading", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS))

import yarrow_simulation as y  # noqa: E402


class TestSecondNameLabel(unittest.TestCase):
    def _text_with_changes(self):
        # find a seed whose reading has changing lines, so both name blocks print
        for seed in range(200):
            r = y.generate_reading(method="yarrow", seed=seed)
            if r["changing_lines"]:
                return r, y.format_reading(r)
        self.fail("no seed in 0-199 produced changing lines")

    def test_text_does_not_credit_second_name_to_huang(self):
        r, text = self._text_with_changes()
        second = r["primary_hexagram"]["huang_name"]
        self.assertIn(f'"{second}"', text)  # the name itself still prints
        self.assertNotIn("Huang:", text)

    def test_json_key_unchanged(self):
        r = y.generate_reading(method="yarrow", seed=0)
        self.assertIn("huang_name", r["primary_hexagram"])


if __name__ == "__main__":
    unittest.main()
