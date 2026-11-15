"""A-Priori for pairs (MMDS §6.2.5) with a triangular array (§6.2.2), plus rule generation."""
import math
from collections import Counter
from functools import lru_cache
from itertools import combinations

import numpy as np
import pandas as pd


def min_count(n, s):
    """Support threshold as a basket count: ceil(s * n), robust to float error."""
    return math.ceil(round(s * n, 9))


@lru_cache(maxsize=32)
def _small_pair_indices(size):
    return np.triu_indices(size, 1)


def pair_indices(size):
    return _small_pair_indices(size) if size <= 64 else np.triu_indices(size, 1)


def run(baskets, threshold):
    """baskets: iterable of sorted tuples of item codes. threshold: absolute count.

    Returns dict with item_counts (all items), frequent (sorted list), pairs {(a, b): count} for frequent pairs (a < b),
    n_candidates (observed pairs), n_candidates_all (C(m, 2)) and triangle storage in bytes."""
    baskets = list(baskets)
    item_counts = Counter(i for t in baskets for i in t)  # pass 1
    frequent = sorted(i for i, c in item_counts.items() if c >= threshold)
    idx = {item: k for k, item in enumerate(frequent)}
    m = len(frequent)
    # pass 2: triangular array, cell for i < j is i*(2m-i-1)/2 + (j-i-1)
    starts = _row_starts(m)
    capacity = m * (m - 1) // 2
    dtype = np.uint32 if len(baskets) <= np.iinfo(np.uint32).max else np.uint64
    tri = np.zeros(capacity, dtype=dtype)
    for t in baskets:
        f = np.array([idx[i] for i in t if i in idx], dtype=np.int64)
        a, b = pair_indices(len(f))
        i, j = f[a], f[b]
        # Each pair has a unique cell within a sorted, deduplicated basket.
        tri[starts[i] + j - i - 1] += 1
    kept = np.flatnonzero((tri > 0) & (tri >= threshold))
    i = np.searchsorted(starts, kept, side="right") - 1
    j = kept - starts[i] + i + 1
    pairs = {(frequent[a], frequent[b]): int(tri[k]) for a, b, k in zip(i, j, kept)}
    observed = int(np.count_nonzero(tri))
    return {"item_counts": item_counts, "frequent": frequent, "pairs": pairs,
            "n_candidates": observed, "n_candidates_all": capacity, "n_occurring": observed,
            "memory_bytes": tri.nbytes}


def _row_starts(m):
    i = np.arange(m, dtype=np.int64)
    return i * (2 * m - i - 1) // 2


def count_frequent_triples(baskets, frequent_pairs, threshold):
    """Join frequent pairs with the same first item, then count surviving triples."""
    suffixes = {}
    for a, b in sorted(frequent_pairs):
        suffixes.setdefault(a, []).append(b)
    candidates = {(a, b, c) for a, neighbors in suffixes.items()
                  for b, c in combinations(neighbors, 2) if (b, c) in frequent_pairs}
    relevant = {item for triple in candidates for item in triple}
    counts = Counter()
    for basket in baskets:
        items = [item for item in basket if item in relevant]
        counts.update(triple for triple in combinations(items, 3) if triple in candidates)
    return sum(count >= threshold for count in counts.values())


def rules(pairs, item_counts, n, min_conf=0.5):
    """Pair rules x -> y with confidence >= min_conf and lift > 1. Returns a DataFrame sorted by confidence."""
    rows = []
    for (a, b), c in pairs.items():
        for x, y in ((a, b), (b, a)):
            conf = c / item_counts[x]
            lift = conf / (item_counts[y] / n)
            if conf >= min_conf and lift > 1:
                rows.append((x, y, c, c / n, conf, lift))
    df = pd.DataFrame(rows, columns=["antecedent", "consequent", "count", "support", "confidence", "lift"])
    return df.sort_values(["confidence", "support", "antecedent", "consequent"],
                          ascending=[False, False, True, True]).reset_index(drop=True)
