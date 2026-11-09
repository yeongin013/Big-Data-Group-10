"""기존 프로젝트의 PCY 함수와 T2 비교표. 구현은 role2_algorithms에 있다."""
from itertools import combinations
import math

import numpy as np
import pandas as pd

from role2_algorithms.basket_mining import BasketDataset, mine_pcy
from role2_algorithms.basket_mining.algorithms.pcy import HASH_MULTIPLIER
from role2_algorithms.basket_mining.benchmark import compare as compare_core

P = HASH_MULTIPLIER


def bucket(i, j, n_buckets):
    if isinstance(n_buckets, bool) or not isinstance(n_buckets, int) or n_buckets < 1:
        raise ValueError("n_buckets must be a positive integer")
    return (i * P + j) % n_buckets


def run(baskets, threshold, n_buckets, max_size=2):
    dataset = BasketDataset.from_rows(baskets)
    result = mine_pcy(dataset, threshold, n_buckets, max_size, capture_buckets=True)
    codes = sorted(result.item_counts)
    ids = {code: i for i, code in enumerate(codes)}
    frequent = sorted(i[0] for i in result.of_size(1))
    counts = result.bucket_counts
    possible = sum(counts[bucket(ids[a], ids[b], n_buckets)] >= threshold
                   for a, b in combinations(frequent, 2))
    observed = result.stats.pair_candidates_observed
    # 기존 보고서용 추정치: 버킷 4바이트, 후보 쌍 레코드 12바이트.
    mem1 = 4 * n_buckets
    mem2 = (n_buckets + 7) // 8 + 12 * observed
    return {"item_counts": result.item_counts, "frequent": frequent,
            "pairs": result.of_size(2), "triples": result.of_size(3),
            "bucket_counts": np.asarray(counts, dtype=np.uint64),
            "frequent_bucket_ratio": result.stats.frequent_bucket_ratio,
            "n_buckets": n_buckets, "n_candidates": observed, "n_candidates_all": possible,
            "memory_pass1_bytes": mem1, "memory_pass2_bytes": mem2,
            "memory_bytes": max(mem1, mem2),
            "memory_kind": "textbook model only; actual counters/bitmap measured separately",
            "stats": result.stats}


def compare(baskets, levels=(0.02, 0.01, 0.005, 0.0025),
            buckets=(65_521, 1_048_573), repeats=5):
    # 정규화는 측정 전에 한 번 수행하고 진단용 버킷 복사는 끈다.
    dataset = BasketDataset.from_rows(baskets)
    rows = compare_core(dataset, levels, buckets, repeats)
    deterministic, timings = [], []
    import platform
    for row in rows:
        is_pcy = row["algorithm"] == "pcy"
        B = row["bucket_count"]
        m = row["frequent_singletons"]
        observed = row["pair_candidates_observed"]
        mem1 = 4 * B if is_pcy else math.nan
        mem2 = (B + 7) // 8 + 12 * observed if is_pcy else 4 * m * (m - 1) // 2
        deterministic.append({
            "level": row["min_support"], "threshold": row["min_count"],
            "algorithm": row["algorithm"], "n_buckets": B if is_pcy else math.nan,
            "n_frequent_items": m, "n_candidates": observed,
            # 모든 후보 열거 비용 O(m²)을 측정에 넣지 않는다.
            "n_candidates_all": math.nan if is_pcy else row["possible_frequent_item_pairs"],
            "possible_frequent_item_pairs": row["possible_frequent_item_pairs"],
            "frequent_bucket_ratio": row["frequent_bucket_ratio"],
            "memory_pass1_bytes": mem1, "memory_pass2_bytes": mem2,
            "memory_bytes": max(mem1, mem2) if is_pcy else mem2,
            "memory_kind": "textbook model; not actual RAM",
            "actual_bucket_counter_payload_bytes": row["bucket_counter_bytes"],
            "actual_bitmap_payload_bytes": row["bitmap_payload_bytes"],
            "n_frequent_pairs": row["frequent_pairs"],
            "pair_occurrences_examined": row["pair_occurrences_examined"],
            "pair_count_updates": row["pair_count_updates"],
        })
        timings.append({"level": row["min_support"], "algorithm": row["algorithm"],
                        "n_buckets": B if is_pcy else math.nan,
                        "median_s": row["median_seconds"], "min_s": row["min_seconds"],
                        "max_s": row["max_seconds"],
                        "tracemalloc_peak_bytes": row["tracemalloc_peak_bytes"],
                        "processor": platform.processor(), "python": platform.python_version(),
                        "repeats": repeats,
                        "memory_scope": "tracked miner allocations; excludes preloaded input; not RSS"})
    return pd.DataFrame(deterministic), pd.DataFrame(timings)


if __name__ == "__main__":
    import sys
    from src import clean
    repeats = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    data = clean.load_baskets().query("year == 1")["items"]
    det, tim = compare(data, repeats=repeats)
    clean.RESULTS.mkdir(exist_ok=True)
    det.to_csv(clean.RESULTS / "pcy_compare.csv", index=False)
    tim.to_csv(clean.RESULTS / "timings.csv", index=False)
    print(det.to_string(index=False))
    print(tim.to_string(index=False))
