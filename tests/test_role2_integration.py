"""Checks for candidate counts, triples and rule thresholds."""
import unittest
from src import apriori, pcy
from tests.test_textbook import BASKETS


class MiningTests(unittest.TestCase):
    def test_pairs_triples_and_strict_lift(self):
        a = apriori.run(BASKETS, 2)
        p = pcy.run(BASKETS, 2, 5)
        self.assertEqual(a["pairs"], p["pairs"])
        self.assertEqual(apriori.count_frequent_triples(BASKETS, a["pairs"], 2), 2)
        independent = apriori.run([("a", "b"), ("a",), ("b",), ()], 1)
        self.assertTrue(apriori.rules(independent["pairs"], independent["item_counts"], 4).empty)
        self.assertEqual(apriori.min_count(100, 0.07), 7)

    def test_compare_uses_same_candidate_definition(self):
        det, timings = pcy.compare(BASKETS, levels=(0.375,), buckets=(5,), repeats=1)
        self.assertEqual(list(det.n_candidates), [6, 5])
        self.assertEqual(list(det.n_frequent_pairs), [3, 3])
        self.assertTrue(all(timings.tracemalloc_peak_bytes > 0))
        self.assertEqual(list(det.n_candidates_all), [6, 5])
        self.assertEqual(det.memory_pass2_bytes.iloc[1], 1 + 12 * 5)
        sparse = [("a", "b"), ("b", "c")]
        result = apriori.run(sparse, 1)
        self.assertEqual((result["n_candidates"], result["n_candidates_all"]), (2, 3))


if __name__ == "__main__":
    unittest.main()
