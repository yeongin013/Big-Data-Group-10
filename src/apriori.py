"""A-Priori for pairs (MMDS §6.2.5) with a triangular array (§6.2.2), plus rule generation."""
import math
from collections import Counter
from itertools import combinations

import numpy as np
import pandas as pd


def min_count(n, s):
    """Support threshold as a basket count: ceil(s * n), robust to float error."""
    return math.ceil(round(s * n, 9))


def run(baskets, threshold):
    """baskets: iterable of sorted tuples of item codes. threshold: absolute count.

    Returns dict with item_counts (all items), frequent (sorted list), pairs {(a, b): count} for frequent pairs (a < b),
    n_candidates (pairs of frequent items, C(m, 2)), n_occurring (candidate pairs seen at least once) and memory_bytes
    (4 bytes per triangular-array cell)."""
    baskets = list(baskets)
    item_counts = Counter(i for t in baskets for i in t)  # pass 1
    frequent = sorted(i for i, c in item_counts.items() if c >= threshold)
    idx = {item: k for k, item in enumerate(frequent)}
    m = len(frequent)
    # pass 2: triangular array, cell for i < j is i*(2m-i-1)/2 + (j-i-1)
    cells = []
    for t in baskets:
        f = [idx[i] for i in t if i in idx]  # t sorted, so f sorted
        cells.extend(i * (2 * m - i - 1) // 2 + (j - i - 1) for i, j in combinations(f, 2))
    tri = np.bincount(np.asarray(cells, dtype=np.int64), minlength=m * (m - 1) // 2)
    pairs = {}
    for k in np.flatnonzero(tri >= threshold):
        i = int(np.searchsorted(_row_starts(m), k, side="right") - 1)
        j = int(k - _row_starts(m)[i] + i + 1)
        pairs[(frequent[i], frequent[j])] = int(tri[k])
    return {"item_counts": item_counts, "frequent": frequent, "pairs": pairs,
            "n_candidates": m * (m - 1) // 2, "n_occurring": int(np.count_nonzero(tri)),
            "memory_bytes": 4 * (m * (m - 1) // 2)}


def _row_starts(m, _cache={}):
    if m not in _cache:
        i = np.arange(m, dtype=np.int64)
        _cache[m] = i * (2 * m - i - 1) // 2
    return _cache[m]


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
