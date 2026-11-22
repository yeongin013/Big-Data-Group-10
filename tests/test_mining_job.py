"""Verify the Solar extension calls the same exact miners as the fixed runs."""

import json
import unittest

from src import apriori, pcy
from src.mining_job import SETTINGS, MiningJob
from tests.test_textbook import BASKETS


class MiningJobTests(unittest.TestCase):
    def test_profile_and_exact_results(self):
        job = MiningJob(iter(BASKETS), 0.25, 10_000_000)
        profile = json.loads(json.dumps(job.profile()))
        expected = apriori.run(BASKETS, 2)
        self.assertEqual(profile["threshold"], 2)
        self.assertEqual(profile["n_frequent_items"], len(expected["frequent"]))
        self.assertEqual(profile["pair_occurrences"], sum(len(b) * (len(b) - 1) // 2 for b in BASKETS))
        for setting in SETTINGS:
            with self.subTest(setting=setting):
                result = job.run(setting)
                stats = profile["settings"][setting]
                self.assertEqual(result["pairs"], expected["pairs"])
                self.assertLessEqual(result["memory_bytes"], stats["modeled_memory_bytes"])
                if setting != "apriori":
                    fixed = pcy.run(BASKETS, 2, stats["n_buckets"])
                    self.assertEqual(stats["frequent_bucket_ratio"], fixed["frequent_bucket_ratio"])

    def test_pilot_uses_sample_support_and_is_repeatable(self):
        job = MiningJob(BASKETS, 0.375, 10_000_000)
        first = job.pilot("pcy_small", sample_size=2, seed=13)
        second = job.pilot("pcy_small", sample_size=2, seed=13)
        self.assertEqual(first["sample_size"], 2)
        self.assertEqual(first["threshold"], 1)
        self.assertGreaterEqual(first.pop("elapsed_s"), 0)
        second.pop("elapsed_s")
        self.assertEqual(first, second)

    def test_rejects_unknown_settings_and_budget_violations(self):
        job = MiningJob(BASKETS, 0.375, 10_000)
        job.validate_setting("apriori")
        with self.assertRaisesRegex(ValueError, "one of"):
            job.run("custom_buckets")
        with self.assertRaisesRegex(ValueError, "exceeds the budget"):
            job.pilot("pcy_small")
        with self.assertRaisesRegex(ValueError, "sample_size"):
            job.pilot("apriori", sample_size=0)
        with self.assertRaisesRegex(ValueError, "support"):
            MiningJob(BASKETS, float("nan"), 10_000)


if __name__ == "__main__":
    unittest.main()
