"""
SDD-TDD tests for the binary (v, c) output mode of yarrow_simulation.py.

Spec (bitwise-encoding):
  Each cast line has value 6/7/8/9 and two binary coordinates:
    v = value   : 1 = yang, 0 = yin
    c = changing : 1 = changing, 0 = stable
  The resulting hexagram's value per line = v XOR c.
    7 -> (1,0)  young yang     8 -> (0,0)  young yin
    9 -> (1,1)  old yang       6 -> (0,1)  old yin

The load-bearing test (test_xor_equivalence): the resulting hexagram derived
through the (v,c) -> XOR path must equal the resulting hexagram the script
already computes via its own changed_line() logic, for every cast. That is the
proof the binary representation is correct — "same result as the normal way."
"""
import os
import sys
import subprocess
import unittest

SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "plugins", "i-ching-reading", "skills", "i-ching-reading", "scripts")
SCRIPT = os.path.join(SCRIPTS, "yarrow_simulation.py")
sys.path.insert(0, os.path.abspath(SCRIPTS))

import yarrow_simulation as y  # noqa: E402


class TestEncoding(unittest.TestCase):
    def test_value_to_vc_map(self):
        self.assertEqual(y.value_to_vc(7), (1, 0))
        self.assertEqual(y.value_to_vc(8), (0, 0))
        self.assertEqual(y.value_to_vc(9), (1, 1))
        self.assertEqual(y.value_to_vc(6), (0, 1))

    def test_round_trip(self):
        for val in (6, 7, 8, 9):
            v, c = y.value_to_vc(val)
            self.assertEqual(y.vc_to_value(v, c), val)

    def test_resulting_value_is_xor(self):
        # resulting line value: 7 (young yang) if v XOR c else 8 (young yin)
        self.assertEqual(y.resulting_line_value(6), 7)   # 0 XOR 1 = 1 -> yang
        self.assertEqual(y.resulting_line_value(7), 7)   # 1 XOR 0 = 1 -> yang
        self.assertEqual(y.resulting_line_value(8), 8)   # 0 XOR 0 = 0 -> yin
        self.assertEqual(y.resulting_line_value(9), 8)   # 1 XOR 1 = 0 -> yin

    def test_xor_matches_changed_line(self):
        # the binary path must agree with the script's own changed_line()
        for val in (6, 7, 8, 9):
            self.assertEqual(y.resulting_line_value(val), y.changed_line(val))


class TestXorEquivalence(unittest.TestCase):
    """The key test: binary-derived resulting hexagram == script's resulting hexagram."""

    def test_equivalence_across_seeds(self):
        checked_changing = 0
        for seed in range(0, 201):
            reading = y.generate_reading(method="yarrow", seed=seed)
            lines = reading["lines"]
            # derive resulting hexagram purely through the (v,c) -> XOR path
            res_vals = [y.resulting_line_value(v) for v in lines]
            res_lower = y.lines_to_trigram(res_vals[0], res_vals[1], res_vals[2])
            res_upper = y.lines_to_trigram(res_vals[3], res_vals[4], res_vals[5])
            xor_hex = y.get_hexagram_number(res_lower, res_upper)

            if reading["changing_lines"]:
                checked_changing += 1
                self.assertEqual(
                    xor_hex, reading["resulting_hexagram"]["number"],
                    msg="seed %d: XOR-derived %d != script %d"
                        % (seed, xor_hex, reading["resulting_hexagram"]["number"]),
                )
            else:
                # no changing lines: XOR is identity, resulting == primary
                self.assertEqual(xor_hex, reading["primary_hexagram"]["number"])
        self.assertGreater(checked_changing, 20, "expected many casts with changing lines")


class TestNonRegression(unittest.TestCase):
    def test_default_text_unchanged_shape(self):
        reading = y.generate_reading(method="yarrow", seed=7)
        default = y.format_reading(reading)              # no binary arg -> default
        explicit = y.format_reading(reading, binary=False)
        self.assertEqual(default, explicit)
        self.assertNotIn("(v, c)", default)              # binary layer absent by default

    def test_binary_output_is_superset(self):
        reading = y.generate_reading(method="yarrow", seed=7)
        default = y.format_reading(reading, binary=False)
        binary = y.format_reading(reading, binary=True)
        # everything in the default reading still appears in binary mode
        core = default.split("=" * 58)[2]                # the body between rules
        for line in core.splitlines():
            if line.strip():
                self.assertIn(line, binary)
        self.assertIn("(v, c)", binary)
        self.assertIn("XOR", binary)

    def test_generate_reading_deterministic(self):
        a = y.generate_reading(method="yarrow", seed=99)
        b = y.generate_reading(method="yarrow", seed=99)
        self.assertEqual(a["lines"], b["lines"])


class TestCLI(unittest.TestCase):
    def _run(self, *extra):
        return subprocess.run([sys.executable, SCRIPT, "--seed", "42", *extra],
                              capture_output=True, text=True)

    def test_binary_flag_runs(self):
        r = self._run("--binary")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("(v, c)", r.stdout)
        self.assertIn("XOR", r.stdout)
        self.assertIn("Resulting", r.stdout)

    def test_default_has_no_binary_layer(self):
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("(v, c)", r.stdout)

    def test_json_unaffected_by_default(self):
        r = self._run("--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("(v, c)", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
