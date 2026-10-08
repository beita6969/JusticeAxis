import math
import unittest

from justiceaxis_eval.families import charge_components, charge_families
from justiceaxis_eval.metrics import (Outcome, Reference, evaluate, log_diff, nearest_anchor, outcome_distance, polarity,
                                      sentence_match, wilson_halfwidth)


class PaperNumbers(unittest.TestCase):
    """Numbers printed in the main results table of the paper (128 cases)."""

    def test_wilson_halfwidths(self):
        self.assertAlmostEqual(100 * wilson_halfwidth(61, 128), 8.53, places=2)   # Acc 47.66
        self.assertAlmostEqual(100 * wilson_halfwidth(70, 128), 8.50, places=2)   # J_gold 54.69

    def test_polarity(self):
        self.assertAlmostEqual(polarity(19, 39), -0.345, places=3)               # J_rig 14.84, J_ung 30.47

    def test_conditionals_and_average(self):
        self.assertAlmostEqual(100 * 61 / 72, 84.72, places=2)                   # Acc/Fam
        self.assertAlmostEqual(100 * 37 / 80, 46.25, places=2)                   # Sent/Disp
        self.assertAlmostEqual((47.66 + 56.25 + 62.50 + 28.91) / 4, 48.83, places=2)

    def test_relative_miss_reduction(self):
        self.assertAlmostEqual(100 * (58 - 19) / 58, 67.24, places=2)   # misses 58/128 -> 19/128


class Distance(unittest.TestCase):
    def test_log_diff_and_rho(self):
        self.assertAlmostEqual(log_diff(0, 0), 0.0)
        self.assertAlmostEqual(log_diff(None, 11), math.log(12))
        smax = 359.0
        rho = outcome_distance("custody_immediate", 24, "custody_immediate", 12, smax)
        self.assertAlmostEqual(rho, 0.5 * abs(math.log(25) - math.log(13)) / math.log(360))
        self.assertAlmostEqual(outcome_distance("fine", None, "custody_immediate", None, smax), 0.5)

    def test_sentence_match(self):
        self.assertTrue(sentence_match(None, 0))
        self.assertTrue(sentence_match(36, 36.0))
        self.assertFalse(sentence_match(36, 35))
        self.assertFalse(sentence_match(None, 12))
        self.assertFalse(sentence_match(12, None))


class Anchors(unittest.TestCase):
    def setUp(self):
        self.ref = Reference("t::main", "robbery", Outcome("custody_immediate", 48), Outcome("custody_immediate", 120),
                             Outcome("acquitted_or_dismissed", 0))

    def test_closest_reference(self):
        w, _ = nearest_anchor(Outcome("custody_immediate", 48), self.ref, 120)
        self.assertEqual(w["gold"], 1.0)
        w, _ = nearest_anchor(Outcome("custody_immediate", 110), self.ref, 120)
        self.assertEqual(w["rigid"], 1.0)
        w, _ = nearest_anchor(Outcome("acquitted_or_dismissed", 0), self.ref, 120)
        self.assertEqual(w["ungrounded"], 1.0)

    def test_ties(self):
        tied = Reference("t::main", "x", Outcome("fine", 0), Outcome("fine", 0), Outcome("custody_immediate", 60))
        w, _ = nearest_anchor(Outcome("fine", 0), tied, 60, tie="gold-first")
        self.assertEqual(w["gold"], 1.0)
        w, _ = nearest_anchor(Outcome("fine", 0), tied, 60, tie="split")
        self.assertEqual((w["gold"], w["rigid"]), (0.5, 0.5))


class EndToEnd(unittest.TestCase):
    def test_oracle_and_rigid_system(self):
        refs = [Reference(f"c{i}::main", "dangerous driving", Outcome("custody_immediate", 12 * (i + 1)),
                          Outcome("custody_immediate", 120), Outcome("acquitted_or_dismissed", 0)) for i in range(4)]
        gold = {r.record_id: {"charge": "dangerous driving", "disposition": r.gold.disposition, "sentence": r.gold.sentence} for r in refs}
        rep, _ = evaluate(refs, gold, bootstrap=0)
        self.assertEqual((rep["Acc"], rep["Disp"], rep["Sent"], rep["J_gold"], rep["Miss"]), (100.0, 100.0, 100.0, 100.0, 0.0))
        rigid = {r.record_id: {"charge": "dangerous driving", "disposition": "custody_immediate", "sentence": 120} for r in refs}
        rep, _ = evaluate(refs, rigid, bootstrap=0)
        self.assertEqual(rep["J_rig"], 100.0)
        self.assertEqual(rep["Pol"], 1.0)

    def test_missing_prediction_counts_wrong(self):
        refs = [Reference("c::main", "fraud", Outcome("fine", 0), Outcome("custody_immediate", 24), Outcome("acquitted_or_dismissed", 0))]
        rep, _ = evaluate(refs, {}, bootstrap=0)
        self.assertEqual((rep["Acc"], rep["Disp"], rep["config"]["n_missing_predictions"]), (0.0, 0.0, 1))


class Charges(unittest.TestCase):
    def test_components_and_families(self):
        self.assertEqual(charge_components("Assault occasioning actual bodily harm (OAPA 1861 s.47)"),
                         charge_components("assault occasioning actual bodily harm"))
        self.assertEqual(charge_families("dangerous driving; possession of a knife"), ["road_traffic", "firearms_weapons"])
        self.assertEqual(charge_families("robbery")[0], "robbery")


if __name__ == "__main__":
    unittest.main()
