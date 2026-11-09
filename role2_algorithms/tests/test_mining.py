"""Independent brute-force oracle, seeded randomized checks, and boundary cases."""
import csv
import json
import random
import tempfile
import unittest
from collections import Counter
from itertools import combinations
from pathlib import Path

from basket_mining import BasketDataset, mine_apriori, mine_pcy, support_to_count, generate_rules
from basket_mining.algorithms.pcy import pack_frequent_buckets, is_frequent_bucket
from basket_mining.extensions.triples import generate_triple_candidates
from basket_mining.io import load_dataset, write_mining_output
from basket_mining.benchmark import compare, save_report

ROOT = Path(__file__).resolve().parents[1]


def brute_force(dataset, threshold, max_size):
    counts = Counter()
    for basket in dataset.baskets:
        for size in range(1, max_size + 1):
            counts.update(combinations(basket, size))
    return {items: count for items, count in counts.items() if count >= threshold}


class MiningTests(unittest.TestCase):
    def setUp(self):
        self.data = load_dataset(ROOT / "examples/baskets.json")

    def test_hand_counted_pairs_and_triple(self):
        for fn in (mine_apriori, mine_pcy):
            result = fn(self.data, 3)
            self.assertEqual(result.item_counts, dict(a=5, b=5, c=4, d=3, e=2))
            self.assertEqual(result.of_size(2), {("a", "b"): 4, ("a", "c"): 3, ("b", "c"): 3})
            self.assertEqual(fn(self.data, 2, max_size=3).of_size(3), {("a", "b", "c"): 2, ("a", "b", "d"): 2})

    def test_randomized_against_independent_oracle(self):
        rng = random.Random(20261107)
        for _ in range(100):
            rows = [[str(i) for i in range(6) if rng.random() < 0.45] for _ in range(rng.randrange(0, 14))]
            dataset = BasketDataset.from_rows(rows)
            threshold = rng.randrange(1, max(2, len(dataset) + 2))
            expected = brute_force(dataset, threshold, 3)
            self.assertEqual(mine_apriori(dataset, threshold, 3).frequent_itemsets, expected)
            for buckets in (1, 2, 5, 101):
                self.assertEqual(mine_pcy(dataset, threshold, buckets, 3).frequent_itemsets, expected)

    def test_collision_false_positive_is_removed(self):
        # B=1 means all pairs collide. ac, bc each count 1, yet the bucket is frequent.
        data = BasketDataset.from_rows([["a", "b"], ["a", "b"], ["a", "c"], ["b", "c"]])
        result = mine_pcy(data, 2, 1)
        self.assertEqual(result.stats.pair_candidates_observed, 3)
        self.assertEqual(result.of_size(2), {("a", "b"): 2})
        self.assertEqual(result.stats.frequent_bucket_ratio, 1)

    def test_packed_bitmap_rounds_up(self):
        bits, count = pack_frequent_buckets([0, 2, 0, 0, 0, 0, 0, 0, 3], 2)
        self.assertEqual(len(bits), 2)
        self.assertEqual(count, 2)
        self.assertEqual([i for i in range(9) if is_frequent_bucket(bits, i)], [1, 8])

    def test_normalization_and_denominator(self):
        data = BasketDataset.from_rows([[" b ", "a", "a"], []])
        self.assertEqual(data.baskets, (("a", "b"), ()))
        rules = generate_rules(mine_apriori(data, 1), 0, 0)
        self.assertEqual(rules[0].support, 0.5)
        for bad in (["abc"], [[None]], [[True]], [[""]]):
            with self.assertRaises(ValueError):
                BasketDataset.from_rows(bad)

    def test_support_ceiling_and_invalid_inputs(self):
        self.assertEqual(support_to_count(100, "0.07"), 7)
        self.assertEqual(support_to_count(3, "0.34"), 2)
        self.assertEqual(support_to_count(100, "0.070000000001"), 8)
        for value in (0, -1, "nan", "Infinity", "abc", 1.1):
            with self.assertRaises(ValueError):
                support_to_count(5, value)
        for threshold in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                mine_apriori(self.data, threshold)
        with self.assertRaises(ValueError):
            mine_pcy(self.data, 1, 0)

    def test_empty_and_no_frequent_pairs(self):
        for rows in ([], [[]], [["a"]], [["a"], ["b"]]):
            data = BasketDataset.from_rows(rows)
            for fn in (mine_apriori, mine_pcy):
                self.assertEqual(fn(data, 1, max_size=3).of_size(2), {})
        self.assertEqual(generate_rules(mine_apriori(BasketDataset.from_rows([]), 1)), [])

    def test_rule_arithmetic_and_filters(self):
        result = mine_apriori(self.data, 3)
        rules = {(r.antecedent, r.consequent): r for r in generate_rules(result)}
        ab = rules[(("a",), ("b",))]
        self.assertAlmostEqual(ab.support, 4 / 8)
        self.assertAlmostEqual(ab.confidence, 4 / 5)
        self.assertAlmostEqual(ab.lift, 1.28)
        self.assertEqual(len(generate_rules(result, 0.8, 1.28)), 2)
        self.assertEqual(generate_rules(result, 0.81, 0), [])
        self.assertEqual(generate_rules(result, 0, 1.29), [])
        independent = mine_apriori(BasketDataset.from_rows([["a", "b"], ["a"], ["b"], []]), 1)
        self.assertEqual(len(generate_rules(independent, 0, 1)), 2)  # lift boundary inclusive
        self.assertEqual(generate_rules(independent, 0, 1.01), [])

    def test_triple_prune_and_rule_directions(self):
        self.assertEqual(generate_triple_candidates({("a", "b"), ("a", "c")}), set())
        result = mine_apriori(BasketDataset.from_rows([["a", "b", "c"]] * 2), 2, 3)
        triple_rules = [r for r in generate_rules(result, 0, 0) if len(r.antecedent) + len(r.consequent) == 3]
        self.assertEqual(len(triple_rules), 6)

    def test_io_and_benchmark_reports(self):
        self.assertEqual(load_dataset(ROOT / "examples/order_lines.csv"), self.data)
        scratch = (ROOT / "outputs" / "test_tmp").resolve()
        scratch.mkdir(parents=True, exist_ok=True)
        # Keep creation and cleanup inside this project's writable output directory.
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            directory = Path(directory)
            result = mine_pcy(self.data, 3, 5)
            write_mining_output(directory, result, generate_rules(result), {"seed": 0})
            doc = json.loads((directory / "itemsets.json").read_text(encoding="utf-8"))
            self.assertEqual(doc["n_baskets"], 8)
            with (directory / "rules.csv").open(encoding="utf-8-sig", newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 6)
            rows = compare(self.data, ["0.375"], [1, 5], repeats=1)
            self.assertEqual(len(rows), 3)
            self.assertEqual({r["frequent_pairs"] for r in rows}, {3})
            self.assertLessEqual(rows[2]["pair_candidates_observed"], rows[0]["pair_candidates_observed"])
            save_report(directory, rows, {"repeats": 1})
            self.assertTrue((directory / "environment.json").exists())
            invalid = directory / "sequence.txt"
            invalid.write_text("1 -1 2 -2\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_dataset(invalid)


if __name__ == "__main__":
    unittest.main()
