"""Profile, sample, and execute the allowed mining settings for the Solar extension."""

from collections import Counter
from copy import deepcopy
from functools import cached_property
from random import Random
from time import perf_counter

import numpy as np

from src import apriori, pcy


# Stable names for the agent tool schema. The value is the PCY bucket count.
SETTINGS = ("apriori", "pcy_small", "pcy_large")
_PCY_BUCKETS = {"pcy_small": 65_521, "pcy_large": 1_048_573}


class MiningJob:
    """One input and support threshold, shared by profiling, pilot, and exact mining."""

    def __init__(self, baskets, support, memory_budget_bytes):
        if type(support) not in (int, float) or not 0 < support <= 1:
            raise ValueError("support must be in (0, 1]")
        if type(memory_budget_bytes) is not int or memory_budget_bytes < 1:
            raise ValueError("memory_budget_bytes must be a positive integer")
        # Same contract as src.clean.load_baskets(): sorted and deduplicated baskets.
        self._baskets = tuple(tuple(basket) for basket in baskets)
        if not self._baskets:
            raise ValueError("expected at least one basket")
        self._support = support
        self._budget = memory_budget_bytes
        self._threshold = self._min_count(len(self._baskets))

    def _min_count(self, size):
        return max(1, apriori.min_count(size, self._support))

    @cached_property
    def _profile(self):
        baskets = self._baskets
        item_counts = Counter(item for basket in baskets for item in basket)
        frequent = {item for item, count in item_counts.items() if count >= self._threshold}
        sizes = [len(basket) for basket in baskets]
        frequent_sizes = [sum(item in frequent for item in basket) for basket in baskets]
        pair_occurrences = sum(k * (k - 1) // 2 for k in sizes)
        frequent_pair_occurrences = sum(k * (k - 1) // 2 for k in frequent_sizes)
        m = len(frequent)
        possible_pairs = m * (m - 1) // 2
        counter_bytes = 4 if len(baskets) <= np.iinfo(np.uint32).max else 8
        estimates = {"apriori": {"modeled_memory_bytes": counter_bytes * possible_pairs}}

        idx = {item: rank for rank, item in enumerate(sorted(item_counts))}
        ids = pcy._encode_baskets(baskets, idx)
        candidate_upper = min(possible_pairs, frequent_pair_occurrences)
        for setting, n_buckets in _PCY_BUCKETS.items():
            counts = pcy._count_buckets(ids, n_buckets)
            frequent_buckets = counts >= self._threshold
            ratio = np.count_nonzero(frequent_buckets) / n_buckets
            # Same storage model as pcy.run; unknown candidate count uses an upper bound.
            passing_occurrences = int(np.sum(counts, where=frequent_buckets))
            candidates = min(candidate_upper, passing_occurrences)
            bitmap_bytes = (n_buckets + 7) // 8
            estimates[setting] = {
                "n_buckets": n_buckets,
                "frequent_bucket_ratio": ratio,
                "modeled_memory_bytes": max(4 * n_buckets, bitmap_bytes + 12 * candidates),
            }

        return {
            "n_baskets": len(baskets),
            "support": self._support,
            "threshold": self._threshold,
            "n_items": len(item_counts),
            "n_frequent_items": m,
            "mean_basket_size": sum(sizes) / len(baskets),
            "max_basket_size": max(sizes),
            "pair_occurrences": pair_occurrences,
            "frequent_item_pair_occurrences": frequent_pair_occurrences,
            "memory_budget_bytes": self._budget,
            "settings": estimates,
        }

    def profile(self):
        """Return aggregate statistics and storage estimates as JSON-ready data."""
        return deepcopy(self._profile)

    def validate_setting(self, setting):
        """Reject unknown settings and choices above the modeled storage budget."""
        if setting not in SETTINGS:
            raise ValueError(f"setting must be one of {', '.join(SETTINGS)}")
        estimate = self._profile["settings"][setting]["modeled_memory_bytes"]
        if estimate > self._budget:
            raise ValueError(f"{setting} modeled storage ({estimate} bytes) exceeds the budget ({self._budget} bytes)")

    def _run(self, setting, baskets, threshold):
        if setting == "apriori":
            return apriori.run(baskets, threshold)
        return pcy.run(baskets, threshold, _PCY_BUCKETS[setting])

    def pilot(self, setting, *, sample_size=1000, seed=0):
        """Time one setting on a uniform sample without replacement. Return aggregates only."""
        if type(sample_size) is not int or sample_size < 1:
            raise ValueError("sample_size must be a positive integer")
        self.validate_setting(setting)
        size = min(sample_size, len(self._baskets))
        rows = Random(seed).sample(range(len(self._baskets)), size)
        sample = [self._baskets[row] for row in rows]
        threshold = self._min_count(size)
        started = perf_counter()
        result = self._run(setting, sample, threshold)
        return {
            "setting": setting,
            "sample_size": size,
            "threshold": threshold,
            "elapsed_s": perf_counter() - started,
            "n_candidates": result["n_candidates"],
            "n_frequent_pairs": len(result["pairs"]),
            "modeled_memory_bytes": result["memory_bytes"],
        }

    def run(self, setting):
        """Mine the full input using the validated setting and existing miner result format."""
        self.validate_setting(setting)
        return self._run(setting, self._baskets, self._threshold)
