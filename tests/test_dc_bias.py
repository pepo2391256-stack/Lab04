import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dc_bias  # noqa: E402


class TestAnalyticalBias(unittest.TestCase):
    def test_divider_typical_fixture(self):
        result = dc_bias.solve_divider(12, 100, 22, 2.2, 1, 100, 0.7)
        self.assertGreater(result["ic_ma"], 0)
        self.assertGreater(result["vb"], 1.8)
        self.assertLess(result["vb"], 2.2)
        self.assertGreater(result["vce"], 0.2)
        self.assertEqual(result["region"], "active")

    def test_fixed_and_emitter_positive(self):
        fixed = dc_bias.solve_fixed(12, 470, 2.2, 100, 0.7)
        emitter = dc_bias.solve_emitter(12, 470, 2.2, 1, 100, 0.7)
        self.assertGreater(fixed["ib_ua"], 0)
        self.assertGreater(emitter["ic_ma"], 0)
        self.assertGreater(emitter["ve"], 0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            dc_bias.solve_emitter(12, 470, 2.2, 0, 100, 0.7)


if __name__ == "__main__":
    unittest.main()
