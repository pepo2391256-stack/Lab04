import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import spice_engine  # noqa: E402


BASE = {
    "vcc": 12,
    "r1": 100,
    "r2": 22,
    "rc": 2.2,
    "re": 1,
    "rl": 10,
    "cin_uf": 10,
    "cout_uf": 10,
    "amp_mv": 10,
    "freq_hz": 1000,
}


class TestValidation(unittest.TestCase):
    def test_valid_fixture(self):
        params = spice_engine.validate_params(BASE)
        self.assertEqual(params["freq_hz"], 1000.0)
        self.assertEqual(params["re"], 1.0)

    def test_re_zero_rejected(self):
        bad = dict(BASE, re=0)
        with self.assertRaises(spice_engine.SimulationError):
            spice_engine.validate_params(bad)

    def test_netlist_contains_analysis(self):
        params = spice_engine.validate_params(BASE)
        netlist = spice_engine.build_netlist(params, "ac", "NPN_MODEL", "test-run")
        self.assertIn(".ac dec 20 1 10MEG", netlist)
        self.assertIn("Q1 collector base emitter NPN_MODEL", netlist)
        self.assertNotIn("shell=True", netlist)


class TestRawParsing(unittest.TestCase):
    def test_transient_raw(self):
        raw = "\n".join(
            [
                "Title: test",
                "Plotname: Transient analysis",
                "Flags: real",
                "No. Variables: 3",
                "No. Points: 2",
                "Variables:",
                "\t0\ttime\ttime",
                "\t1\tv(in)\tvoltage",
                "\t2\tv(out)\tvoltage",
                "Values:",
                "\t0\t0.0\t0.01\t1.0",
                "\t1\t0.001\t-0.01\t0.5",
            ]
        )
        parsed = spice_engine.parse_raw(raw)
        self.assertEqual(len(parsed["rows"]), 2)
        transient = spice_engine.extract_tran(parsed)
        self.assertAlmostEqual(transient["vin_mv"][0], 10.0)
        self.assertAlmostEqual(transient["vout_v"][1], 0.5)

    def test_cutoff_none_when_flat(self):
        self.assertEqual(spice_engine.find_cutoff([1, 10], [1, 1]), (None, None))


if __name__ == "__main__":
    unittest.main()
