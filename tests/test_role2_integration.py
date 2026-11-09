"""Contract checks between independent role-2 code and the team's existing API."""
import unittest
from src import apriori, pcy
from tests.test_textbook import BASKETS


class AdapterTests(unittest.TestCase):
    def test_pairs_triples_and_strict_lift(self):
        a = apriori.run(BASKETS, 2, max_size=3)
        p = pcy.run(BASKETS, 2, 5, max_size=3)
        self.assertEqual(a["pairs"], p["pairs"])
        self.assertEqual(a["triples"], p["triples"])
        independent = apriori.run([("a", "b"), ("a",), ("b",), ()], 1)
        self.assertTrue(apriori.rules(independent["pairs"], independent["item_counts"], 4).empty)
        self.assertEqual(apriori.min_count(100, 0.07), 7)

    def test_compare_uses_same_candidate_definition(self):
        det, timings = pcy.compare(BASKETS, levels=(0.375,), buckets=(5,), repeats=1)
        self.assertEqual(list(det.n_candidates), [6, 5])
        self.assertEqual(list(det.n_frequent_pairs), [3, 3])
        self.assertTrue(all(timings.tracemalloc_peak_bytes > 0))
        self.assertEqual(det.actual_bitmap_payload_bytes.iloc[1], 1)
        self.assertTrue(det.memory_kind.str.contains("textbook").all())


if __name__ == "__main__":
    unittest.main()
