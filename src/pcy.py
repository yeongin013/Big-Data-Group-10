"""PCY for pairs (MMDS §6.3.1), and a timing/memory comparison against A-Priori (§6.2.5)."""
import platform
import time
import tracemalloc
from collections import Counter

import numpy as np
import pandas as pd

from src import apriori

P = 1_000_003  # hash multiplier, fixed by plan §3.1


def bucket(i, j, n_buckets):
    """Hash of the pair (i, j), i < j. Deterministic, unlike Python hash()."""
    return (i * P + j) % n_buckets


def _pairs(ids, _tri={}):
    """All pairs i < j of a sorted id array, as two arrays."""
    k = len(ids)
    if k not in _tri:
        _tri[k] = np.triu_indices(k, 1)
    a, b = _tri[k]
    return ids[a], ids[b]


def run(baskets, threshold, n_buckets):
    """baskets: iterable of sorted tuples of item codes. threshold: absolute count. n_buckets: number of hash buckets.

    Same item_counts / frequent / pairs as apriori.run, plus bucket_counts, frequent_bucket_ratio, candidate counts
    and textbook memory per pass."""
    baskets = list(baskets)
    # item ids: sort codes, so i < j iff code_i < code_j (baskets are sorted tuples, so id arrays come out sorted)
    codes = sorted({i for t in baskets for i in t})
    idx = {c: k for k, c in enumerate(codes)}
    ids = [np.array([idx[i] for i in t], dtype=np.int64) for t in baskets]

    # pass 1: count items, and hash every pair of every basket into a bucket count (§6.3.1)
    item_counts = Counter(i for t in baskets for i in t)
    bucket_counts = np.zeros(n_buckets, dtype=np.int64)
    for s in range(0, len(ids), 1000):  # ponytail: chunks of 1000 baskets keep the hash arrays small
        h = [bucket(*_pairs(x), n_buckets) for x in ids[s:s + 1000]]
        bucket_counts += np.bincount(np.concatenate(h), minlength=n_buckets)

    # between passes: frequent items, and the bucket array replaced by a bitmap (1 bit per bucket)
    frequent = sorted(i for i, c in item_counts.items() if c >= threshold)
    is_freq_item = np.zeros(len(codes), dtype=bool)
    is_freq_item[[idx[i] for i in frequent]] = True
    bitmap = bucket_counts >= threshold

    # pass 2: count only candidate pairs = both items frequent AND pair hashes to a frequent bucket
    keys = []
    for x in ids:
        x = x[is_freq_item[x]]
        a, b = _pairs(x)
        keep = bitmap[bucket(a, b, n_buckets)]
        keys.append(a[keep] * len(codes) + b[keep])  # pair -> one int64 key, stands in for the (i, j, count) triple
    uniq, counts = np.unique(np.concatenate(keys) if keys else np.empty(0, np.int64), return_counts=True)
    pairs = {(codes[k // len(codes)], codes[k % len(codes)]): int(c)
             for k, c in zip(uniq, counts) if c >= threshold}

    # all C(m, 2) pairs of frequent items that pass the bitmap, occurring or not (comparable to apriori n_candidates)
    f = np.flatnonzero(is_freq_item)
    n_candidates_all = int(bitmap[bucket(*_pairs(f), n_buckets)].sum())

    n_candidates = len(uniq)  # candidate pairs actually seen in pass 2 = triples stored
    mem1 = 4 * n_buckets  # pass 1: 4-byte count per bucket
    mem2 = n_buckets // 8 + 12 * n_candidates  # pass 2: bitmap + 12-byte triple per candidate (§6.2.2)
    return {"item_counts": item_counts, "frequent": frequent, "pairs": pairs,
            "bucket_counts": bucket_counts, "n_buckets": n_buckets,
            "frequent_bucket_ratio": float(bitmap.mean()),
            "n_candidates": n_candidates, "n_candidates_all": n_candidates_all,
            "memory_pass1_bytes": mem1, "memory_pass2_bytes": mem2, "memory_bytes": max(mem1, mem2)}


def _timed(f, repeats):
    """Run f repeats times for wall time, then once more under tracemalloc (it slows code, so not timed)."""
    secs = []
    for _ in range(repeats):
        t = time.perf_counter()
        out = f()
        secs.append(time.perf_counter() - t)
    tracemalloc.start()
    f()
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return out, secs, peak


def compare(baskets, levels=(0.02, 0.01, 0.005, 0.0025), buckets=(65_521, 1_048_573), repeats=5):
    """A-Priori vs PCY at each support level. Returns (deterministic table, timings table)."""
    baskets = list(baskets)
    n = len(baskets)
    det, tim = [], []
    env = {"processor": platform.processor(), "python": platform.python_version(), "repeats": repeats}
    for s in levels:
        t = apriori.min_count(n, s)
        a, secs, peak = _timed(lambda: apriori.run(baskets, t), repeats)
        det.append({"level": s, "threshold": t, "algorithm": "apriori", "n_buckets": np.nan,
                    "n_frequent_items": len(a["frequent"]), "n_candidates": a["n_candidates"],
                    "n_candidates_all": a["n_candidates"], "frequent_bucket_ratio": np.nan,
                    "memory_pass1_bytes": np.nan, "memory_pass2_bytes": a["memory_bytes"],
                    "memory_bytes": a["memory_bytes"], "n_frequent_pairs": len(a["pairs"])})
        tim.append({"level": s, "algorithm": "apriori", "n_buckets": np.nan, **_stats(secs, peak), **env})
        for B in buckets:
            p, secs, peak = _timed(lambda: run(baskets, t, B), repeats)
            assert p["pairs"] == a["pairs"], f"PCY != A-Priori at support {s}, B={B}"
            det.append({"level": s, "threshold": t, "algorithm": "pcy", "n_buckets": B,
                        "n_frequent_items": len(p["frequent"]), "n_candidates": p["n_candidates"],
                        "n_candidates_all": p["n_candidates_all"],
                        "frequent_bucket_ratio": p["frequent_bucket_ratio"],
                        "memory_pass1_bytes": p["memory_pass1_bytes"], "memory_pass2_bytes": p["memory_pass2_bytes"],
                        "memory_bytes": p["memory_bytes"], "n_frequent_pairs": len(p["pairs"])})
            tim.append({"level": s, "algorithm": "pcy", "n_buckets": B, **_stats(secs, peak), **env})
    return pd.DataFrame(det), pd.DataFrame(tim)


def _stats(secs, peak):
    return {"median_s": float(np.median(secs)), "min_s": min(secs), "max_s": max(secs), "tracemalloc_peak_bytes": peak}


if __name__ == "__main__":
    import sys
    from src import clean
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    y1 = clean.load_baskets().query("year == 1")["items"]
    t0 = time.perf_counter()
    det, tim = compare(y1, repeats=repeats)
    clean.RESULTS.mkdir(exist_ok=True)
    det.to_csv(clean.RESULTS / "pcy_compare.csv", index=False)
    tim.to_csv(clean.RESULTS / "timings.csv", index=False)
    pd.set_option("display.width", 200)
    print(det.to_string(index=False))
    print(tim.drop(columns=["processor", "python", "repeats"]).to_string(index=False))
    print(f"total {time.perf_counter() - t0:.1f}s, repeats={repeats}")
