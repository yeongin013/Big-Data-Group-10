"""Profile, sample, and execute the allowed mining settings for the Solar extension."""

from collections import Counter
from copy import deepcopy
from functools import cached_property
from math import log1p
from random import Random
from time import perf_counter

import numpy as np

from src import apriori, pcy


# Stable names for the agent tool schema. The value is the PCY bucket count.
SETTINGS = ("apriori", "pcy_small", "pcy_large")
_PCY_BUCKETS = {"pcy_small": 65_521, "pcy_large": 1_048_573}
_EXACT_PAIR_LIMIT = 1 << 24
_SKETCH_SLOTS = 1 << 20


def _mix_pair_ids(pair_ids):
    """Mix dense pair IDs before mapping them to sketch slots (SplitMix64 finalizer)."""
    keys = pair_ids.astype(np.uint64)
    keys = (keys ^ (keys >> 30)) * np.uint64(0xBF58476D1CE4E5B9)
    keys = (keys ^ (keys >> 27)) * np.uint64(0x94D049BB133111EB)
    return keys ^ (keys >> 31)


def _count_pcy_candidates(ids, ranks, bucket_masks, n_possible_pairs):
    """Count occupied slots for observed candidate pairs under each bucket mask."""
    exact = n_possible_pairs <= _EXACT_PAIR_LIMIT
    n_slots = n_possible_pairs if exact else _SKETCH_SLOTS
    bitmaps = {size: np.zeros((n_slots + 7) // 8, dtype=np.uint8) for size in bucket_masks}
    starts = apriori._row_starts(int(np.count_nonzero(ranks >= 0)))
    for start in range(0, len(ids), 128):
        pairs = [pcy._pairs(basket[ranks[basket] >= 0]) for basket in ids[start:start + 128]]
        left, right = zip(*pairs)
        a, b = np.concatenate(left), np.concatenate(right)
        i, j = ranks[a], ranks[b]
        slots = starts[i] + j - i - 1
        if not exact:
            slots = (_mix_pair_ids(slots) % n_slots).astype(np.intp)
        for size, mask in bucket_masks.items():
            kept = slots[mask[pcy.bucket(a, b, size)]]
            # Multiple slots can share one byte. Accumulate every bit in that byte.
            np.bitwise_or.at(bitmaps[size], kept // 8, (1 << (kept % 8)).astype(np.uint8))
    return {size: (int(np.bitwise_count(bitmap).sum()), exact) for size, bitmap in bitmaps.items()}


def _candidate_estimate(occupied, exact, upper):
    if exact:
        return occupied, "exact"
    if occupied >= 0.95 * _SKETCH_SLOTS:
        return upper, "upper_bound"
    estimate = round(-_SKETCH_SLOTS * log1p(-occupied / _SKETCH_SLOTS))
    return min(estimate, upper), "bitmap_estimate"


def _pcy_memory_bytes(n_buckets, n_candidates):
    bitmap_bytes = (n_buckets + 7) // 8
    return max(4 * n_buckets, bitmap_bytes + 12 * n_candidates)


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
        ranks = np.full(len(idx), -1, dtype=np.int64)
        ranks[[idx[item] for item in sorted(frequent)]] = np.arange(m)
        candidate_upper = min(possible_pairs, frequent_pair_occurrences)
        bucket_masks = {}
        upper_bounds = {}
        for n_buckets in _PCY_BUCKETS.values():
            counts = pcy._count_buckets(ids, n_buckets)
            frequent_buckets = counts >= self._threshold
            passing_occurrences = int(np.sum(counts, where=frequent_buckets))
            bucket_masks[n_buckets] = frequent_buckets
            upper_bounds[n_buckets] = min(candidate_upper, passing_occurrences)
            del counts
        occupied = _count_pcy_candidates(ids, ranks, bucket_masks, possible_pairs)
        for setting, n_buckets in _PCY_BUCKETS.items():
            upper = upper_bounds[n_buckets]
            candidates, method = _candidate_estimate(*occupied[n_buckets], upper)
            estimates[setting] = {
                "n_buckets": n_buckets,
                "frequent_bucket_ratio": float(np.count_nonzero(bucket_masks[n_buckets]) / n_buckets),
                "n_candidates_estimate": candidates,
                "candidate_count_method": method,
                "modeled_memory_bytes": _pcy_memory_bytes(n_buckets, candidates),
                "modeled_memory_upper_bound_bytes": _pcy_memory_bytes(
                    n_buckets, candidates if method == "exact" else upper
                ),
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
        stats = self._profile["settings"][setting]
        estimate = stats.get("modeled_memory_upper_bound_bytes", stats["modeled_memory_bytes"])
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
